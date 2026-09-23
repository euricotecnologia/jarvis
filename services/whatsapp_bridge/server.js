const express = require('express');
const cors = require('cors');
const path = require('path');
const fs = require('fs');
const QRCode = require('qrcode');
const pino = require('pino');
const {
    default: makeWASocket,
    DisconnectReason,
    useMultiFileAuthState,
    fetchLatestBaileysVersion,
    makeCacheableSignalKeyStore
} = require('@whiskeysockets/baileys');

const PORT = process.env.PORT || 25874;
const SESSION_DIR = process.env.SESSION_DIR || path.join(__dirname, '..', '..', 'data', 'whatsapp_session');

// Cria diretório de sessão se não existir
if (!fs.existsSync(SESSION_DIR)) {
    fs.mkdirSync(SESSION_DIR, { recursive: true });
}

const app = express();
app.use(cors());
app.use(express.json());

// Logger silencioso para Baileys
const logger = pino({ level: 'silent' });

let sock = null;
let connectionStatus = 'disconnected'; // 'disconnected' | 'connecting' | 'qr_ready' | 'connected'
let currentQrDataUri = '';
let currentUser = null;
let sseClients = [];
let recentLogs = [];

function addLog(type, message, details = {}) {
    const entry = {
        id: Date.now().toString(36) + Math.random().toString(36).substr(2, 4),
        type, // 'info' | 'success' | 'warning' | 'error' | 'sent' | 'received'
        message,
        details,
        timestamp: new Date().toISOString()
    };
    recentLogs.unshift(entry);
    if (recentLogs.length > 50) recentLogs.pop();
    broadcast('log', entry);
}

function broadcast(event, data) {
    const payload = `event: ${event}\ndata: ${JSON.stringify(data)}\n\n`;
    sseClients.forEach(res => {
        try {
            res.write(payload);
        } catch (e) {
            // Ignora cliente desconectado
        }
    });
}

function formatJid(phone) {
    let clean = (phone || '').toString().replace(/[^0-9]/g, '');
    if (!clean) return '';
    if (clean.includes('@')) return clean;
    return `${clean}@s.whatsapp.net`;
}

async function startWhatsApp() {
    try {
        if (connectionStatus === 'connected' && sock) {
            return;
        }

        connectionStatus = 'connecting';
        broadcast('status', { status: connectionStatus });

        const { state, saveCreds } = await useMultiFileAuthState(SESSION_DIR);
        const { version } = await fetchLatestBaileysVersion();

        sock = makeWASocket({
            version,
            logger,
            printQRInTerminal: false,
            auth: {
                creds: state.creds,
                keys: makeCacheableSignalKeyStore(state.keys, logger)
            },
            generateHighQualityLinkPreview: true,
            syncFullHistory: false
        });

        sock.ev.on('creds.update', saveCreds);

        sock.ev.on('connection.update', async (update) => {
            const { connection, lastDisconnect, qr } = update;

            if (qr) {
                try {
                    currentQrDataUri = await QRCode.toDataURL(qr, {
                        margin: 2,
                        width: 340,
                        color: {
                            dark: '#0284C7',
                            light: '#FFFFFF'
                        }
                    });
                    connectionStatus = 'qr_ready';
                    broadcast('status', {
                        status: connectionStatus,
                        qrCode: currentQrDataUri
                    });
                    addLog('info', 'Novo QR Code gerado para conexão.');
                } catch (qrErr) {
                    console.error('Erro ao gerar QR Code:', qrErr);
                }
            }

            if (connection === 'close') {
                const statusCode = lastDisconnect?.error?.output?.statusCode;
                const shouldReconnect = statusCode !== DisconnectReason.loggedOut;
                
                connectionStatus = 'disconnected';
                currentQrDataUri = '';
                currentUser = null;

                addLog('warning', `Conexão fechada. Código: ${statusCode || 'desconhecido'}.`);
                broadcast('status', { status: connectionStatus, user: null });

                if (shouldReconnect) {
                    addLog('info', 'Tentando reconectar ao WhatsApp em 3 segundos...');
                    setTimeout(() => startWhatsApp(), 3000);
                } else {
                    addLog('error', 'Sessão desconectada pelo usuário ou WhatsApp.');
                }
            } else if (connection === 'open') {
                connectionStatus = 'connected';
                currentQrDataUri = '';

                const user = sock.user || {};
                const id = user.id || '';
                const phone = id.split(':')[0] || id.split('@')[0] || '';
                const name = user.name || user.notify || phone;

                currentUser = {
                    id,
                    phone,
                    name
                };

                addLog('success', `WhatsApp Conectado! Número: +${phone} (${name})`);
                broadcast('status', {
                    status: connectionStatus,
                    user: currentUser
                });
            }
        });

        // Mensagens recebidas
        sock.ev.on('messages.upsert', async (m) => {
            if (m.type === 'notify') {
                for (const msg of m.messages) {
                    if (!msg.key.fromMe) {
                        const from = msg.key.remoteJid || '';
                        const text = msg.message?.conversation ||
                                     msg.message?.extendedTextMessage?.text ||
                                     msg.message?.imageMessage?.caption || '';
                        const senderName = msg.pushName || from;

                        if (text) {
                            addLog('received', `Mensagem recebida de ${senderName}: "${text.substring(0, 40)}${text.length > 40 ? '...' : ''}"`, {
                                from,
                                text,
                                senderName
                            });
                            broadcast('message', {
                                from,
                                text,
                                senderName,
                                timestamp: msg.messageTimestamp
                            });
                        }
                    }
                }
            }
        });

    } catch (err) {
        console.error('Erro ao inicializar Baileys:', err);
        connectionStatus = 'disconnected';
        addLog('error', `Falha ao iniciar WhatsApp: ${err.message}`);
        broadcast('status', { status: connectionStatus });
    }
}

// ------------------------------------------------------------- Rotas HTTP
app.get('/health', (req, res) => {
    res.json({ ok: true, version: '6.7.24', bridge: 'Jarvis Baileys Bridge' });
});

app.get('/status', (req, res) => {
    res.json({
        status: connectionStatus,
        qrCode: currentQrDataUri,
        user: currentUser,
        connected: connectionStatus === 'connected',
        logs: recentLogs.slice(0, 20)
    });
});

app.post('/connect', async (req, res) => {
    if (connectionStatus !== 'connected') {
        startWhatsApp();
    }
    res.json({ success: true, status: connectionStatus });
});

app.post('/disconnect', async (req, res) => {
    try {
        if (sock) {
            await sock.logout();
        }
    } catch (e) {
        // Ignora
    }
    try {
        if (fs.existsSync(SESSION_DIR)) {
            fs.rmSync(SESSION_DIR, { recursive: true, force: true });
            fs.mkdirSync(SESSION_DIR, { recursive: true });
        }
    } catch (e) {
        // Ignora
    }
    connectionStatus = 'disconnected';
    currentQrDataUri = '';
    currentUser = null;
    broadcast('status', { status: connectionStatus, user: null });
    addLog('info', 'WhatsApp desconectado e credenciais limpas.');
    res.json({ success: true });
});

app.post('/send', async (req, res) => {
    const { to, text } = req.body;
    if (!to || !text) {
        return res.status(400).json({ success: false, error: 'Parâmetros "to" e "text" são obrigatórios.' });
    }

    if (connectionStatus !== 'connected' || !sock) {
        return res.status(503).json({ success: false, error: 'WhatsApp não está conectado no momento.' });
    }

    const jid = formatJid(to);
    if (!jid) {
        return res.status(400).json({ success: false, error: 'Número de telefone inválido.' });
    }

    try {
        const sent = await sock.sendMessage(jid, { text: text.trim() });
        const messageId = sent?.key?.id || '';
        addLog('sent', `Mensagem enviada para ${to}: "${text.substring(0, 40)}${text.length > 40 ? '...' : ''}"`, {
            to,
            text,
            messageId
        });
        res.json({ success: true, messageId, to });
    } catch (err) {
        console.error('Erro ao enviar mensagem:', err);
        addLog('error', `Falha ao enviar para ${to}: ${err.message}`);
        res.status(500).json({ success: false, error: err.message });
    }
});

// SSE endpoint para eventos em tempo real
app.get('/events', (req, res) => {
    res.setHeader('Content-Type', 'text/event-stream');
    res.setHeader('Cache-Control', 'no-cache');
    res.setHeader('Connection', 'keep-alive');
    res.flushHeaders();

    sseClients.push(res);

    // Envia status inicial imediatamente
    res.write(`event: status\ndata: ${JSON.stringify({
        status: connectionStatus,
        qrCode: currentQrDataUri,
        user: currentUser
    })}\n\n`);

    req.on('close', () => {
        sseClients = sseClients.filter(client => client !== res);
    });
});

app.listen(PORT, '127.0.0.1', () => {
    console.log(`[Jarvis WhatsApp Bridge] Rodando em http://127.0.0.1:${PORT}`);
    // Inicia conexão automaticamente ao subir
    startWhatsApp();
});
