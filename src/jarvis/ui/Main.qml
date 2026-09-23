import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window
import QtQuick.Dialogs

ApplicationWindow {
    id: window
    width: 1600
    height: 940
    minimumWidth: 1240
    minimumHeight: 760
    visible: true
    visibility: Window.Maximized
    title: (jarvisBackend.systemName ? jarvisBackend.systemName.toUpperCase() : "JARVIS") + " // PERSONAL INTELLIGENCE"
    readonly property bool isDark: jarvisBackend.currentTheme !== "light"
    color: isDark ? "#050816" : "#F0F4F8"
    flags: Qt.Window | Qt.FramelessWindowHint

    onClosing: function(close) {
        if (!exitConfirmDialog.forceExit) {
            close.accepted = false
            exitConfirmDialog.open()
        }
    }

    // Cores Semânticas Adaptativas ao Tema
    readonly property color cyan: isDark ? "#46EAF7" : "#0284C7"
    readonly property color violet: isDark ? "#8B5CF6" : "#7C3AED"
    readonly property color green: isDark ? "#4EF2A6" : "#16A34A"
    readonly property color amber: isDark ? "#F6C453" : "#D97706"
    readonly property color danger: isDark ? "#FF7A90" : "#DC2626"
    readonly property color panel: isDark ? "#0A1022" : "#FFFFFF"
    readonly property color panelSub: isDark ? "#0D1D33" : "#F8FAFC"
    readonly property color panelHeader: isDark ? "#081324" : "#EDF2F7"
    readonly property color cardBorder: isDark ? "#18324F" : "#CBD5E1"
    readonly property color textPrimary: isDark ? "#EAFBFF" : "#0F172A"
    readonly property color textMuted: isDark ? "#7893A8" : "#64748B"
    readonly property color dialogBg: isDark ? "#0A1526" : "#FFFFFF"
    readonly property color dialogBorder: isDark ? "#26516A" : "#CBD5E1"
    readonly property color divider: isDark ? "#142840" : "#E2E8F0"
    readonly property color inputBg: isDark ? "#0D1D33" : "#FFFFFF"
    readonly property color inputBorder: isDark ? "#23435E" : "#CBD5E1"

    readonly property bool voiceActive: jarvisBackend.voiceState !== "idle" && jarvisBackend.voiceState !== "error"
    readonly property bool listening: jarvisBackend.voiceState === "listening"
    readonly property bool speaking: jarvisBackend.voiceState === "speaking"
    readonly property string orbMode: listening ? "listening"
        : speaking ? "speaking"
        : (jarvisBackend.voiceState === "transcribing" || jarvisBackend.voiceState === "thinking" || jarvisBackend.busy) ? "thinking"
        : "idle"

    property var stats: jarvisBackend.systemStats
    property var wx: jarvisBackend.weather
    property date now: new Date()
    property int activePatientId: -1  // setor Saúde: paciente aberto no prontuário

    Timer {
        interval: 1000; running: true; repeat: true
        onTriggered: window.now = new Date()
    }

    Component.onCompleted: {
        if (jarvisSettingsPreview) {
            settingsDialog.tab = jarvisPermissionsPreview ? 1 : 0
            settingsDialog.open()
        }
    }

    function pct(node) { return node && node.percent !== undefined ? node.percent : 0 }

    // ─── Componente padrão Jarvis ─────────────────────────────────────────────
    // variant: "primary" | "secondary" | "danger" | "save" | "success" | "amber" | "close" | "icon"
    component JarvisButton : Button {
        id: jBtn
        property string variant: "primary"
        property int textSize: 10
        readonly property bool isSquareIcon: variant === "close" || variant === "icon" || text === "✕" || text === "🗑" || text === "✎" || text === "⟳" || text === "↻"
        property int customRadius: isSquareIcon ? 8 : 10
        implicitHeight: isSquareIcon ? 32 : 40
        implicitWidth: isSquareIcon ? 32 : (btnLabel.implicitWidth + leftPadding + rightPadding + 6)
        Layout.preferredWidth: isSquareIcon ? 32 : implicitWidth
        Layout.preferredHeight: isSquareIcon ? 32 : implicitHeight
        Layout.alignment: Qt.AlignVCenter
        leftPadding: isSquareIcon ? 0 : 14
        rightPadding: isSquareIcon ? 0 : 14
        topPadding: 0
        bottomPadding: 0
        background: Rectangle {
            radius: jBtn.customRadius
            color: {
                if (window.isDark) {
                    if (jBtn.variant === "close")     return jBtn.hovered ? "#3D1A25" : "#0F1E32"
                    if (jBtn.variant === "icon")      return jBtn.hovered ? "#14364C" : "#0D2438"
                    if (jBtn.variant === "danger")    return jBtn.hovered ? "#512030" : "#241724"
                    if (jBtn.variant === "secondary") return jBtn.hovered ? "#172840" : "#101D31"
                    if (jBtn.variant === "success")   return jBtn.enabled ? (jBtn.hovered ? "#1C6E4A" : "#155238") : "#1A2A38"
                    if (jBtn.variant === "amber")     return jBtn.hovered ? "#3A2A10" : "#241B0B"
                    // "primary" & "save"
                    return jBtn.enabled ? (jBtn.hovered ? "#14364C" : "#0D2438") : "#0A1826"
                } else {
                    if (jBtn.variant === "close")     return jBtn.hovered ? "#FEE2E2" : "#F1F5F9"
                    if (jBtn.variant === "icon")      return jBtn.hovered ? "#BAE6FD" : "#E0F2FE"
                    if (jBtn.variant === "danger")    return jBtn.hovered ? "#FECACA" : "#FEE2E2"
                    if (jBtn.variant === "secondary") return jBtn.hovered ? "#E2E8F0" : "#F1F5F9"
                    if (jBtn.variant === "success")   return jBtn.enabled ? (jBtn.hovered ? "#BBF7D0" : "#DCFCE7") : "#F1F5F9"
                    if (jBtn.variant === "amber")     return jBtn.hovered ? "#FEF08A" : "#FEF9C3"
                    // "primary" & "save"
                    return jBtn.enabled ? (jBtn.hovered ? "#BAE6FD" : "#E0F2FE") : "#F1F5F9"
                }
            }
            border.color: {
                if (window.isDark) {
                    if (jBtn.variant === "close")     return jBtn.hovered ? "#7A2E40" : "#22394E"
                    if (jBtn.variant === "icon")      return jBtn.hovered ? cyan : "#24566A"
                    if (jBtn.variant === "danger")    return jBtn.hovered ? "#8A3048" : "#5A2A3A"
                    if (jBtn.variant === "secondary") return jBtn.hovered ? "#3A5875" : "#294057"
                    if (jBtn.variant === "success")   return jBtn.enabled ? (jBtn.hovered ? "#35BD7D" : green) : "#2A3F52"
                    if (jBtn.variant === "amber")     return jBtn.hovered ? "#FAD889" : amber
                    // "primary" & "save"
                    return jBtn.enabled ? (jBtn.hovered ? cyan : "#24566A") : "#1A3348"
                } else {
                    if (jBtn.variant === "close")     return jBtn.hovered ? "#F87171" : "#CBD5E1"
                    if (jBtn.variant === "icon")      return jBtn.hovered ? cyan : "#0284C7"
                    if (jBtn.variant === "danger")    return jBtn.hovered ? "#EF4444" : "#FCA5A5"
                    if (jBtn.variant === "secondary") return jBtn.hovered ? "#94A3B8" : "#CBD5E1"
                    if (jBtn.variant === "success")   return jBtn.enabled ? (jBtn.hovered ? "#22C55E" : "#86EFAC") : "#CBD5E1"
                    if (jBtn.variant === "amber")     return jBtn.hovered ? "#EAB308" : "#FDE047"
                    // "primary" & "save"
                    return jBtn.enabled ? (jBtn.hovered ? "#0369A1" : "#0284C7") : "#CBD5E1"
                }
            }
            opacity: jBtn.down ? 0.75 : 1
            clip: true
        }
        contentItem: Text {
            id: btnLabel
            text: jBtn.text
            color: {
                if (window.isDark) {
                    if (jBtn.variant === "close")     return jBtn.hovered ? "#FFAFC0" : textMuted
                    if (jBtn.variant === "icon")      return jBtn.enabled ? cyan : textMuted
                    if (jBtn.variant === "danger")    return jBtn.hovered ? "#FFAFC0" : "#FF9AAE"
                    if (jBtn.variant === "secondary") return jBtn.hovered ? textPrimary : textMuted
                    if (jBtn.variant === "success")   return jBtn.enabled ? "#B7F5D6" : "#5C7286"
                    if (jBtn.variant === "amber")     return jBtn.hovered ? "#FFE7B8" : "#F6D9A0"
                    // "primary" & "save"
                    return jBtn.enabled ? cyan : "#3E5570"
                } else {
                    if (jBtn.variant === "close")     return jBtn.hovered ? "#DC2626" : textMuted
                    if (jBtn.variant === "icon")      return jBtn.enabled ? cyan : textMuted
                    if (jBtn.variant === "danger")    return jBtn.hovered ? "#B91C1C" : "#DC2626"
                    if (jBtn.variant === "secondary") return jBtn.hovered ? textPrimary : textMuted
                    if (jBtn.variant === "success")   return jBtn.enabled ? "#15803D" : "#94A3B8"
                    if (jBtn.variant === "amber")     return jBtn.hovered ? "#B45309" : "#D97706"
                    // "primary" & "save"
                    return jBtn.enabled ? "#0369A1" : "#64748B"
                }
            }
            font.pixelSize: jBtn.textSize
            font.weight: Font.DemiBold
            font.letterSpacing: 1.1
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
            elide: Text.ElideRight
        }
    }
    // ─────────────────────────────────────────────────────────────────────────

    ListModel {
        id: chatModel
        ListElement {
            role: "system"
            body: "Núcleo inicializado. Estou conectado ao seu sistema local e pronto para receber instruções."
            meta: "JARVIS CORE"
            image: ""
            filePath: ""
            fileName: ""
            code: ""
            language: ""
            previewable: false
        }
    }

    function chatRow(role, body, meta) {
        return {
            "role": role, "body": body, "meta": meta,
            "image": "", "filePath": "", "fileName": "",
            "code": "", "language": "", "previewable": false
        }
    }

    Connections {
        target: jarvisBackend
        function onMessageAdded(role, content, meta) {
            chatModel.append(window.chatRow(role, content, meta))
            chatView.positionViewAtEnd()
        }
        function onChatCleared() {
            chatModel.clear()
        }
        function onChatMediaAdded(m) {
            var row = window.chatRow(m.role || "assistant", m.caption || "", m.meta || "")
            row.image = (m.kind === "image" ? (m.uri || "") : "")
            row.filePath = m.filePath || ""
            row.fileName = m.fileName || ""
            chatModel.append(row)
            chatView.positionViewAtEnd()
        }
        function onChatArtifactAdded(a) {
            var row = window.chatRow("assistant", "", (a.filename || "CÓDIGO").toUpperCase())
            row.code = a.code || ""
            row.language = a.language || "texto"
            row.fileName = a.filename || "código.txt"
            row.previewable = a.previewable === true
            chatModel.append(row)
            chatView.positionViewAtEnd()
        }
        function onChatBodyReplaced(text) {
            for (var i = chatModel.count - 1; i >= 0; i--) {
                if (chatModel.get(i).role === "assistant" && chatModel.get(i).code === "") {
                    chatModel.setProperty(i, "body", text)
                    break
                }
            }
        }
        function onStreamStarted(meta) {
            chatModel.append(window.chatRow("assistant", "", meta))
            chatView.positionViewAtEnd()
        }
        function onStreamDelta(text) {
            if (chatModel.count === 0)
                return
            var last = chatModel.count - 1
            chatModel.setProperty(last, "body", chatModel.get(last).body + text)
            chatView.positionViewAtEnd()
        }
        function onStreamEnded(meta) {
            if (chatModel.count === 0)
                return
            var last = chatModel.count - 1
            if (meta && meta.length > 0)
                chatModel.setProperty(last, "meta", meta)
            if (chatModel.get(last).body.length === 0)
                chatModel.setProperty(last, "body", "(sem resposta)")
            chatView.positionViewAtEnd()
        }
        function onConfirmationRequested(token, description) {
            confirmDialog.token = token
            confirmDialog.description = description
            confirmDialog.open()
        }
        function onNotificationRequested(info) {
            notifyDialog.push(info)
        }
        function onComposeRequested(text) {
            jarvisBackend.setView("hub")
            inputArea.forceActiveFocus()
            inputArea.text = text
            inputArea.cursorPosition = text.length
        }
        function onVisionTested(dataUri, result) {
            webcamTest.imageUri = dataUri
            webcamTest.result = result
            webcamTest.loading = false
            if (!webcamTest.visible) webcamTest.open()
        }
        function onServerTested(alias, result) {
            serverManager.testAlias = alias
            serverManager.testResult = result
            serverManager.testing = false
        }
        function onProfileFolderNeeded(profileId) {
            devFolderDialog.pendingProfile = profileId
            devFolderDialog.open()
        }
    }

    // ---------------------------------------------------------------- fundo
    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            GradientStop { position: 0.0; color: window.isDark ? "#081429" : "#F8FAFC" }
            GradientStop { position: 0.5; color: window.isDark ? "#050816" : "#F0F4F8" }
            GradientStop { position: 1.0; color: window.isDark ? "#09051B" : "#E2E8F0" }
        }

        Canvas {
            id: bgGridCanvas
            anchors.fill: parent
            opacity: window.isDark ? 0.06 : 0.04
            Connections {
                target: window
                function onIsDarkChanged() { bgGridCanvas.requestPaint() }
            }
            onPaint: {
                var ctx = getContext("2d")
                ctx.reset()
                ctx.strokeStyle = window.isDark ? "#46EAF7" : "#0284C7"
                ctx.lineWidth = 1
                var step = 52
                for (var x = 0; x < width; x += step) {
                    ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, height); ctx.stroke()
                }
                for (var y = 0; y < height; y += step) {
                    ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(width, y); ctx.stroke()
                }
            }
        }
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        // ------------------------------------------------------------ topo
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 64
            color: window.isDark ? "#070D1C" : "#FFFFFF"
            border.color: window.isDark ? "#152A42" : "#CBD5E1"
            border.width: 1

            MouseArea {
                anchors.fill: parent
                acceptedButtons: Qt.LeftButton
                onPressed: window.startSystemMove()
            }

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 22
                anchors.rightMargin: 14
                spacing: 16

                Rectangle {
                    width: 30; height: 30; radius: 15
                    color: "transparent"
                    border.color: cyan
                    border.width: 2
                    Rectangle {
                        anchors.centerIn: parent
                        width: 9; height: 9; radius: 5
                        color: cyan
                        SequentialAnimation on opacity {
                            loops: Animation.Infinite
                            NumberAnimation { to: 0.25; duration: 900 }
                            NumberAnimation { to: 1.0; duration: 900 }
                        }
                    }
                }

                Row {
                    spacing: 8
                    Text {
                        text: jarvisBackend.systemName ? jarvisBackend.systemName.toUpperCase() : "JARVIS"
                        color: textPrimary
                        font.pixelSize: 19
                        font.weight: Font.DemiBold
                        font.letterSpacing: 4
                        anchors.verticalCenter: parent.verticalCenter
                    }
                    Text {
                        text: jarvisBackend.appVersion
                        color: textMuted
                        font.pixelSize: 9
                        anchors.verticalCenter: parent.verticalCenter
                    }
                    Row {
                        spacing: 5
                        anchors.verticalCenter: parent.verticalCenter
                        Rectangle { width: 6; height: 6; radius: 3; color: green; anchors.verticalCenter: parent.verticalCenter }
                        Text { text: "ONLINE"; color: green; font.pixelSize: 9; font.letterSpacing: 1.5; anchors.verticalCenter: parent.verticalCenter }
                    }
                }

                Item { width: 6 }

                Rectangle {
                    id: statusPill
                    Layout.preferredWidth: statusRow.implicitWidth + 24
                    Layout.minimumWidth: statusRow.implicitWidth + 24
                    height: 30
                    radius: 15
                    color: window.isDark ? "#0B2530" : "#E0F2FE"
                    border.color: window.isDark ? "#1B6370" : "#BAE6FD"
                    Row {
                        id: statusRow
                        anchors.centerIn: parent
                        spacing: 8
                        Rectangle {
                            width: 7; height: 7; radius: 4
                            anchors.verticalCenter: parent.verticalCenter
                            color: listening ? "#FF6B8A" : jarvisBackend.busy ? amber : green
                        }
                        Text {
                            id: statusText
                            anchors.verticalCenter: parent.verticalCenter
                            text: jarvisBackend.status
                            color: listening ? "#FF9AAE" : jarvisBackend.busy ? amber : (window.isDark ? "#8BF7C2" : "#16A34A")
                            font.pixelSize: 9
                            font.weight: Font.DemiBold
                            font.letterSpacing: 1.1
                        }
                    }
                }

                Item { Layout.fillWidth: true }

                Column {
                    spacing: 1
                    Text {
                        anchors.right: parent.right
                        text: window.now.toLocaleDateString(Qt.locale("pt_BR"), "dddd, d 'de' MMMM 'de' yyyy").toUpperCase()
                        color: textMuted
                        font.pixelSize: 9
                        font.letterSpacing: 1.4
                    }
                    Text {
                        anchors.right: parent.right
                        text: window.now.toLocaleTimeString(Qt.locale("pt_BR"), "HH:mm:ss")
                        color: cyan
                        font.pixelSize: 15
                        font.weight: Font.DemiBold
                        font.letterSpacing: 2
                    }
                }

                Item { width: 10 }

                // Alternador Rápido de Tema Claro / Escuro
                JarvisButton {
                    variant: "secondary"
                    customRadius: 8
                    implicitHeight: 32
                    leftPadding: 10
                    rightPadding: 10
                    textSize: 8
                    text: window.isDark ? "☀️  TEMA CLARO" : "🌙  TEMA ESCURO"
                    onClicked: jarvisBackend.setTheme(window.isDark ? "light" : "dark")
                    ToolTip.visible: hovered
                    ToolTip.text: window.isDark ? "Alternar para o Tema Claro" : "Alternar para o Tema Escuro"
                    ToolTip.delay: 300
                }

                Item { width: 8 }

                Repeater {
                    model: ["─", "🗖", "✕"]
                    delegate: Button {
                        width: 36; height: 32
                        text: modelData
                        background: Rectangle {
                            radius: 8
                            color: parent.hovered
                                   ? (index === 2 ? (window.isDark ? "#6A2431" : "#FEE2E2") : (window.isDark ? "#14233A" : "#E2E8F0"))
                                   : "transparent"
                        }
                        contentItem: Text {
                            text: parent.text
                            color: index === 2 && parent.hovered
                                   ? (window.isDark ? "#FFB0BC" : "#DC2626")
                                   : textMuted
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                            font.pixelSize: index === 0 ? 12 : (index === 1 ? 11 : 13)
                            font.weight: Font.DemiBold
                        }
                        onClicked: {
                            if (index === 0) window.showMinimized()
                            else if (index === 1) window.visibility === Window.Maximized ? window.showNormal() : window.showMaximized()
                            else exitConfirmDialog.open()
                        }
                    }
                }
            }
        }

        // ----------------------------------------------------------- corpo
        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 0

            // -------------------------------------------------- lateral
            Rectangle {
                Layout.preferredWidth: 214
                Layout.fillHeight: true
                color: window.isDark ? "#070D1D" : "#FFFFFF"
                border.color: window.isDark ? "#12243C" : "#CBD5E1"
                border.width: 1

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 16
                    spacing: 6

                    Text {
                        text: "COMANDO CENTRAL"
                        color: textMuted
                        font.pixelSize: 8
                        font.letterSpacing: 2
                        Layout.topMargin: 6
                        Layout.bottomMargin: 6
                    }

                    Repeater {
                        model: jarvisBackend.navItems
                        delegate: Rectangle {
                            required property var modelData
                            required property int index
                            Layout.fillWidth: true
                            Layout.preferredHeight: 42
                            radius: 10
                            readonly property bool current: jarvisBackend.currentView === modelData.key
                            color: current ? (window.isDark ? "#102D42" : "#E0F2FE")
                                           : (navMouse.containsMouse ? (window.isDark ? "#0E1B30" : "#F1F5F9") : "transparent")
                            border.color: current ? (window.isDark ? "#245D70" : "#BAE6FD") : "transparent"

                            Rectangle {
                                visible: parent.current
                                width: 3; height: 20; radius: 2
                                color: cyan
                                anchors.left: parent.left
                                anchors.verticalCenter: parent.verticalCenter
                            }

                            Row {
                                anchors.verticalCenter: parent.verticalCenter
                                anchors.left: parent.left
                                anchors.leftMargin: 16
                                spacing: 12
                                Text {
                                    text: modelData.glyph
                                    color: parent.parent.current ? cyan : textMuted
                                    font.pixelSize: 15
                                    anchors.verticalCenter: parent.verticalCenter
                                }
                                Text {
                                    text: (jarvisBackend.viewLabels && jarvisBackend.viewLabels[modelData.key])
                                          ? jarvisBackend.viewLabels[modelData.key] : modelData.label
                                    color: parent.parent.current ? textPrimary : textMuted
                                    font.pixelSize: 10
                                    font.weight: Font.DemiBold
                                    font.letterSpacing: 1.1
                                    anchors.verticalCenter: parent.verticalCenter
                                }
                            }
                            MouseArea {
                                id: navMouse
                                anchors.fill: parent
                                hoverEnabled: true
                                onClicked: {
                                    if (modelData.key === "config") {
                                        settingsDialog.tab = 0
                                        settingsDialog.open()
                                    } else {
                                        jarvisBackend.setView(modelData.key)
                                    }
                                }
                            }
                        }
                    }

                    Item { Layout.fillHeight: true }

                    RingGauge {
                        Layout.alignment: Qt.AlignHCenter
                        implicitWidth: 140
                        implicitHeight: 140
                        value: stats && stats.performance !== undefined ? stats.performance : 0
                        accent: cyan
                        fontSize: 30
                    }
                    Text {
                        Layout.alignment: Qt.AlignHCenter
                        text: "NÍVEL DE DESEMPENHO"
                        color: textMuted
                        font.pixelSize: 8
                        font.letterSpacing: 1.4
                    }

                    JarvisButton {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 40
                        Layout.topMargin: 8
                        text: "+  NOVA CONVERSA"
                        onClicked: jarvisBackend.newConversation()
                    }
                }
            }

            // -------------------------------------------------- centro
            Item {
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 20
                    spacing: 16

                    RowLayout {
                        Layout.fillWidth: true
                        Text {
                            text: "VISÃO GERAL DO SISTEMA"
                            color: textPrimary
                            font.pixelSize: 18
                            font.weight: Font.DemiBold
                            font.letterSpacing: 2
                        }
                        Item { Layout.fillWidth: true }
                        Text {
                            text: "CANAL SEGURO  //  " + jarvisBackend.activeProvider.toUpperCase()
                            color: cyan
                            opacity: 0.7
                            font.pixelSize: 9
                            font.letterSpacing: 1.3
                        }
                    }

                    // linha 1: metricas + núcleo
                    RowLayout {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        Layout.preferredHeight: 400
                        Layout.minimumHeight: 300
                        spacing: 14

                        ColumnLayout {
                            Layout.preferredWidth: 210
                            Layout.minimumWidth: 150
                            Layout.maximumWidth: 232
                            Layout.fillHeight: true
                            spacing: 14
                            MetricCard {
                                Layout.fillWidth: true; Layout.fillHeight: true
                                title: "CPU"; glyph: "\u25A0"; accent: cyan
                                primary: stats && stats.cpu ? stats.cpu.primary : "--"
                                secondary: stats && stats.cpu ? stats.cpu.secondary : ""
                                percent: pct(stats ? stats.cpu : null)
                            }
                            MetricCard {
                                Layout.fillWidth: true; Layout.fillHeight: true
                                title: "MEMÓRIA"; glyph: "\u25A4"; accent: violet
                                primary: stats && stats.memory ? stats.memory.primary : "--"
                                secondary: stats && stats.memory ? stats.memory.secondary : ""
                                percent: pct(stats ? stats.memory : null)
                            }
                            MetricCard {
                                Layout.fillWidth: true; Layout.fillHeight: true
                                title: "GPU"; glyph: "\u25C6"; accent: green
                                primary: stats && stats.gpu ? stats.gpu.primary : "--"
                                secondary: stats && stats.gpu ? (stats.gpu.label + "  " + stats.gpu.secondary) : ""
                                percent: pct(stats ? stats.gpu : null)
                            }
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            Layout.minimumWidth: 240
                            radius: 16
                            color: window.isDark ? "#091126" : "#FFFFFF"
                            border.color: window.isDark ? "#162B47" : "#CBD5E1"

                            VoiceOrb {
                                id: coreOrb
                                anchors.centerIn: parent
                                width: Math.min(parent.width * 0.86, parent.height * 0.92)
                                height: width
                                mode: window.orbMode
                                level: jarvisBackend.voiceLevel
                                cyan: window.cyan
                                violet: window.violet
                                isDarkTheme: window.isDark
                            }

                            MouseArea {
                                anchors.centerIn: parent
                                width: coreOrb.width * 0.5
                                height: coreOrb.height * 0.5
                                enabled: speaking
                                cursorShape: speaking ? Qt.PointingHandCursor : Qt.ArrowCursor
                                onClicked: jarvisBackend.stopSpeaking()
                                ToolTip.visible: speaking && containsMouse
                                ToolTip.text: "Parar a resposta"
                                hoverEnabled: true
                            }

                            Text {
                                anchors.left: parent.left
                                anchors.top: parent.top
                                anchors.margins: 14
                                text: "NÚCLEO NEURAL"
                                color: textMuted
                                font.pixelSize: 8
                                font.letterSpacing: 1.6
                            }
                            Text {
                                anchors.right: parent.right
                                anchors.bottom: parent.bottom
                                anchors.margins: 14
                                horizontalAlignment: Text.AlignRight
                                text: "SYNC 100%\nLOCAL CORE"
                                color: violet
                                opacity: 0.6
                                font.pixelSize: 8
                                font.letterSpacing: 1.1
                                lineHeight: 1.4
                            }
                        }

                        ColumnLayout {
                            Layout.preferredWidth: 210
                            Layout.minimumWidth: 150
                            Layout.maximumWidth: 232
                            Layout.fillHeight: true
                            spacing: 14
                            MetricCard {
                                Layout.fillWidth: true; Layout.fillHeight: true
                                title: "REDE"; glyph: "\u21C5"; accent: cyan
                                primary: stats && stats.network ? stats.network.primary : "--"
                                secondary: stats && stats.network ? stats.network.secondary : ""
                                percent: pct(stats ? stats.network : null)
                            }
                            MetricCard {
                                Layout.fillWidth: true; Layout.fillHeight: true
                                title: "ARMAZENAMENTO"; glyph: "\u25A9"; accent: amber
                                primary: stats && stats.storage ? stats.storage.primary : "--"
                                secondary: stats && stats.storage ? stats.storage.secondary : ""
                                percent: pct(stats ? stats.storage : null)
                            }
                            MetricCard {
                                Layout.fillWidth: true; Layout.fillHeight: true
                                title: "SEGURANÇA"; glyph: "\u26E8"; accent: green
                                primary: stats && stats.security ? stats.security.primary : "--"
                                secondary: stats && stats.security ? stats.security.secondary : ""
                                percent: pct(stats ? stats.security : null)
                            }
                        }
                    }

                    // linha 2: clima + análises
                    RowLayout {
                        Layout.fillWidth: true
                        Layout.fillHeight: false
                        Layout.preferredHeight: 236
                        spacing: 14

                        Rectangle {
                            Layout.preferredWidth: 360
                            Layout.fillHeight: true
                            radius: 16
                            color: window.isDark ? "#0A1428" : "#FFFFFF"
                            border.color: window.isDark ? "#152A44" : "#CBD5E1"

                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: 18
                                spacing: 6

                                RowLayout {
                                    Layout.fillWidth: true
                                    Text { text: "CLIMA"; color: cyan; font.pixelSize: 10; font.weight: Font.DemiBold; font.letterSpacing: 1.6 }
                                    Item { Layout.fillWidth: true }
                                    Text {
                                        text: wx && wx.updated_at ? wx.updated_at : ""
                                        color: textMuted; font.pixelSize: 8
                                    }
                                }

                                Text {
                                    text: wx && wx.city ? (wx.city + (wx.region ? ", " + wx.region : "")) : jarvisBackend.weatherCity
                                    color: textPrimary
                                    font.pixelSize: 13
                                    Layout.fillWidth: true
                                    elide: Text.ElideRight
                                }

                                RowLayout {
                                    Layout.fillWidth: true
                                    Layout.topMargin: 2
                                    spacing: 12
                                    Text {
                                        text: {
                                            var k = wx && wx.icon ? wx.icon : "cloud"
                                            var m = {"sun":"\u2600","moon":"\u263E","cloud-sun":"\u2600",
                                                     "cloud":"\u2601","fog":"\u2601","drizzle":"\u2602",
                                                     "rain":"\u2602","snow":"\u2746","storm":"\u2607"}
                                            return m[k] ? m[k] : "\u2601"
                                        }
                                        color: cyan
                                        font.pixelSize: 46
                                    }
                                    Column {
                                        Layout.fillWidth: true
                                        Text {
                                            text: wx && wx.ok ? (Math.round(wx.temperature_c) + "\u00B0C") : "--"
                                            color: textPrimary
                                            font.pixelSize: 34
                                            font.weight: Font.Light
                                        }
                                        Text {
                                            text: wx && wx.ok ? wx.description : (wx && wx.error ? wx.error : "Carregando...")
                                            color: textMuted
                                            font.pixelSize: 10
                                            width: 190
                                            wrapMode: Text.Wrap
                                        }
                                    }
                                }

                                Item { Layout.fillHeight: true }

                                RowLayout {
                                    Layout.fillWidth: true
                                    Repeater {
                                        model: [
                                            {"k": "Umidade", "v": wx && wx.ok ? wx.humidity + "%" : "--"},
                                            {"k": "Vento", "v": wx && wx.ok ? Math.round(wx.wind_kmh) + " km/h" : "--"},
                                            {"k": "Sensação", "v": wx && wx.ok ? Math.round(wx.feels_like_c) + "\u00B0" : "--"}
                                        ]
                                        delegate: Column {
                                            Layout.fillWidth: true
                                            spacing: 3
                                            Text { text: modelData.k; color: textMuted; font.pixelSize: 8; font.letterSpacing: 1 }
                                            Text { text: modelData.v; color: textPrimary; font.pixelSize: 12; font.weight: Font.Medium }
                                        }
                                    }
                                }
                            }
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            radius: 16
                            color: window.isDark ? "#0A1428" : "#FFFFFF"
                            border.color: window.isDark ? "#152A44" : "#CBD5E1"

                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: 18
                                spacing: 10

                                Text { text: "ANÁLISES DO SISTEMA"; color: cyan; font.pixelSize: 10; font.weight: Font.DemiBold; font.letterSpacing: 1.6 }

                                RowLayout {
                                    Layout.fillWidth: true
                                    Layout.preferredHeight: 96
                                    RingGauge {
                                        Layout.fillWidth: true; Layout.fillHeight: true
                                        value: stats && stats.performance !== undefined ? stats.performance : 0
                                        caption: "DESEMPENHO"; accent: cyan; fontSize: 19
                                    }
                                    RingGauge {
                                        Layout.fillWidth: true; Layout.fillHeight: true
                                        value: stats && stats.efficiency !== undefined ? stats.efficiency : 0
                                        caption: "EFICIENCIA"; accent: violet; fontSize: 19
                                    }
                                    RingGauge {
                                        Layout.fillWidth: true; Layout.fillHeight: true
                                        value: stats && stats.health !== undefined ? stats.health : 0
                                        caption: "SAUDE"; accent: green; fontSize: 19
                                    }
                                }

                                Text { text: "ATIVIDADE EM TEMPO REAL"; color: textMuted; font.pixelSize: 8; font.letterSpacing: 1.4 }

                                Sparkline {
                                    Layout.fillWidth: true
                                    Layout.fillHeight: true
                                    v1: pct(stats ? stats.cpu : null)
                                    v2: pct(stats ? stats.memory : null)
                                    v3: pct(stats ? stats.network : null)
                                    c1: cyan; c2: violet; c3: green
                                }

                                RowLayout {
                                    Layout.fillWidth: true
                                    spacing: 16
                                    Repeater {
                                        model: [
                                            {"k": "CPU", "c": cyan}, {"k": "MEMÓRIA", "c": violet}, {"k": "REDE", "c": green}
                                        ]
                                        delegate: Row {
                                            spacing: 6
                                            Rectangle { width: 8; height: 3; radius: 2; color: modelData.c; anchors.verticalCenter: parent.verticalCenter }
                                            Text { text: modelData.k; color: textMuted; font.pixelSize: 8; font.letterSpacing: 1 }
                                        }
                                    }
                                }
                            }
                        }

                        // Card: Sugestões Proativas & Cognição
                        Rectangle {
                            Layout.preferredWidth: 320
                            Layout.fillHeight: true
                            radius: 16
                            color: window.isDark ? "#0A1428" : "#FFFFFF"
                            border.color: window.isDark ? "#152A44" : "#CBD5E1"

                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: 16
                                spacing: 8

                                RowLayout {
                                    Layout.fillWidth: true
                                    Text {
                                        text: "SUGESTÕES PROATIVAS"
                                        color: cyan
                                        font.pixelSize: 10
                                        font.weight: Font.DemiBold
                                        font.letterSpacing: 1.4
                                    }
                                    Item { Layout.fillWidth: true }
                                    Rectangle {
                                        implicitHeight: 18
                                        implicitWidth: cogLabel.implicitWidth + 10
                                        radius: 9
                                        color: window.isDark ? "#10291F" : "#DCFCE7"
                                        Text {
                                            id: cogLabel
                                            anchors.centerIn: parent
                                            text: "● Cognição Ativa"
                                            color: green
                                            font.pixelSize: 7
                                            font.weight: Font.Bold
                                        }
                                    }
                                }

                                Text {
                                    text: "Ações sugeridas com base em seus hábitos e contexto:"
                                    color: textMuted
                                    font.pixelSize: 9
                                    Layout.fillWidth: true
                                    elide: Text.ElideRight
                                }

                                ColumnLayout {
                                    Layout.fillWidth: true
                                    Layout.fillHeight: true
                                    spacing: 6

                                    Repeater {
                                        model: (jarvisBackend.proactiveSuggestions || []).slice(0, 3)
                                        delegate: Rectangle {
                                            Layout.fillWidth: true
                                            Layout.fillHeight: true
                                            radius: 8
                                            color: hubSugMouse.containsMouse ? (window.isDark ? "#122A42" : "#E0F2FE") : (window.isDark ? "#060D19" : "#F8FAFC")
                                            border.color: hubSugMouse.containsMouse ? cyan : (window.isDark ? "#14283E" : "#E2E8F0")
                                            border.width: 1

                                            RowLayout {
                                                anchors.fill: parent
                                                anchors.margins: 8
                                                spacing: 8

                                                Text { text: modelData.icon || "💡"; font.pixelSize: 14 }

                                                ColumnLayout {
                                                    Layout.fillWidth: true
                                                    spacing: 1
                                                    Text {
                                                        text: modelData.title || "Sugestão"
                                                        color: textPrimary
                                                        font.pixelSize: 10
                                                        font.weight: Font.DemiBold
                                                    }
                                                    Text {
                                                        text: modelData.text || ""
                                                        color: textMuted
                                                        font.pixelSize: 8
                                                        elide: Text.ElideRight
                                                        Layout.fillWidth: true
                                                    }
                                                }

                                                Text {
                                                    text: "▶"
                                                    color: hubSugMouse.containsMouse ? cyan : textMuted
                                                    font.pixelSize: 9
                                                }
                                            }

                                            MouseArea {
                                                id: hubSugMouse
                                                anchors.fill: parent
                                                hoverEnabled: true
                                                cursorShape: Qt.PointingHandCursor
                                                onClicked: jarvisBackend.executeProactiveSuggestion(modelData.action || modelData.text)
                                            }
                                        }
                                    }
                                }

                                JarvisButton {
                                    Layout.fillWidth: true
                                    variant: "secondary"
                                    text: "🧠  Gerenciar Memória & Cognição"
                                    implicitHeight: 28
                                    textSize: 8
                                    onClicked: memoryManagerModal.open()
                                }
                            }
                        }
                    }
                }

                // painel da Agenda (compromissos + contatos)
                Rectangle {
                    id: agendaPanel
                    objectName: "agendaPanel"
                    anchors.fill: parent
                    anchors.margins: 20
                    visible: jarvisBackend.currentView === "agenda"
                    radius: 16
                    color: window.isDark ? "#070E1E" : "#FFFFFF"
                    border.color: window.isDark ? "#152A44" : "#CBD5E1"
                    property int agendaTab: 0

                    component GridHeader : Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 30
                        color: window.isDark ? "#0A1526" : "#F1F5F9"
                        radius: 6
                        default property alias content: hrow.data
                        RowLayout {
                            id: hrow
                            anchors.fill: parent
                            anchors.leftMargin: 14
                            anchors.rightMargin: 12
                            spacing: 12
                        }
                    }
                    component HeaderCell : Text {
                        color: textMuted
                        font.pixelSize: 8
                        font.weight: Font.DemiBold
                        font.letterSpacing: 1.2
                    }

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 22
                        spacing: 12

                        Column {
                            spacing: 3
                            Text {
                                text: "AGENDA"
                                color: textPrimary
                                font.pixelSize: 17
                                font.weight: Font.DemiBold
                                font.letterSpacing: 2
                            }
                            Text {
                                text: "Compromissos, contatos e lembretes por voz. Pergunte: \"jarvis, o que tenho hoje?\"."
                                color: textMuted
                                font.pixelSize: 10
                            }
                        }

                        // abas
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 4
                            Repeater {
                                model: [
                                    {"t": "COMPROMISSOS", "i": 0},
                                    {"t": "CONTATOS", "i": 1}
                                ]
                                delegate: Rectangle {
                                    Layout.preferredWidth: 150
                                    Layout.preferredHeight: 38
                                    color: "transparent"
                                    readonly property bool sel: agendaPanel.agendaTab === modelData.i
                                    Text {
                                        anchors.centerIn: parent
                                        text: modelData.t
                                        color: parent.sel ? cyan : textMuted
                                        font.pixelSize: 10
                                        font.weight: Font.DemiBold
                                        font.letterSpacing: 1.2
                                    }
                                    Rectangle {
                                        anchors.bottom: parent.bottom
                                        anchors.left: parent.left
                                        anchors.right: parent.right
                                        height: 2
                                        color: parent.sel ? cyan : (window.isDark ? "#1E3A55" : "#E2E8F0")
                                    }
                                    MouseArea { anchors.fill: parent; onClicked: agendaPanel.agendaTab = modelData.i }
                                }
                            }
                            Item { Layout.fillWidth: true }
                        }

                        // ============ COMPROMISSOS ============
                        ColumnLayout {
                            visible: agendaPanel.agendaTab === 0
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            spacing: 8

                            RowLayout {
                                Layout.fillWidth: true
                                Text {
                                    Layout.fillWidth: true
                                    text: apptList.count + " compromisso(s)"
                                    color: textMuted; font.pixelSize: 9; font.letterSpacing: 1
                                }
                                JarvisButton {
                                    variant: "amber"
                                    text: "🔔  TESTAR NOTIFICACAO"
                                    leftPadding: 12; rightPadding: 12
                                    onClicked: jarvisBackend.testNotification()
                                }
                                JarvisButton {
                                    text: "+  ADICIONAR COMPROMISSO"
                                    onClicked: appointmentEditor.openNew()
                                }
                            }

                            GridHeader {
                                HeaderCell { text: "QUANDO"; Layout.preferredWidth: 170 }
                                HeaderCell { text: "TÍTULO"; Layout.fillWidth: true }
                                HeaderCell { text: "LOCAL"; Layout.preferredWidth: 150 }
                                HeaderCell { text: "CONTATO"; Layout.preferredWidth: 130 }
                                HeaderCell { text: "LEMBRETE"; Layout.preferredWidth: 110 }
                                HeaderCell { text: ""; Layout.preferredWidth: 96 }
                            }

                            ListView {
                                id: apptList
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                clip: true
                                model: jarvisBackend.appointments
                                ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }

                                delegate: Rectangle {
                                    width: apptList.width
                                    height: 46
                                    color: modelData.isPast ? "transparent" : (index % 2 === 0 ? (window.isDark ? "#0A1526" : "#FFFFFF") : (window.isDark ? "#0B1A30" : "#F8FAFC"))
                                    opacity: modelData.isPast ? 0.5 : 1
                                    Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: window.isDark ? "#132A44" : "#E2E8F0" }

                                    RowLayout {
                                        anchors.fill: parent
                                        anchors.leftMargin: 14
                                        anchors.rightMargin: 12
                                        spacing: 12

                                        Row {
                                            Layout.preferredWidth: 170
                                            spacing: 6
                                            Text { text: modelData.whenText.split("  ")[0]; color: cyan; font.pixelSize: 11; font.weight: Font.DemiBold; anchors.verticalCenter: parent.verticalCenter }
                                            Text {
                                                anchors.verticalCenter: parent.verticalCenter
                                                text: modelData.whenText.indexOf("(") >= 0 ? modelData.whenText.substring(modelData.whenText.indexOf("(")) : ""
                                                color: amber; font.pixelSize: 8
                                            }
                                        }
                                        Text { Layout.fillWidth: true; text: modelData.title; color: textPrimary; font.pixelSize: 12; font.weight: Font.Medium; elide: Text.ElideRight }
                                        Text { Layout.preferredWidth: 150; text: modelData.location || "—"; color: textMuted; font.pixelSize: 10; elide: Text.ElideRight }
                                        Text { Layout.preferredWidth: 130; text: modelData.contactName || "—"; color: textMuted; font.pixelSize: 10; elide: Text.ElideRight }
                                        Text { Layout.preferredWidth: 110; text: modelData.reminderMinutes >= 0 ? modelData.reminderText : "—"; color: modelData.reminderMinutes >= 0 ? (window.isDark ? "#F6D9A0" : "#B45309") : textMuted; font.pixelSize: 9; elide: Text.ElideRight }
                                        Row {
                                            Layout.preferredWidth: 70
                                            spacing: 6
                                            JarvisButton {
                                                text: "✎"
                                                width: 32; height: 32
                                                textSize: 12
                                                ToolTip.visible: hovered
                                                ToolTip.text: "Editar compromisso"
                                                ToolTip.delay: 300
                                                onClicked: appointmentEditor.openEdit(modelData)
                                            }
                                            JarvisButton {
                                                variant: "danger"
                                                text: "✕"
                                                width: 32; height: 32
                                                textSize: 12
                                                ToolTip.visible: hovered
                                                ToolTip.text: "Excluir compromisso"
                                                ToolTip.delay: 300
                                                onClicked: { agendaDelete.kind = "appointment"; agendaDelete.pending = modelData; agendaDelete.open() }
                                            }
                                        }
                                    }
                                }

                                Text {
                                    anchors.centerIn: parent
                                    visible: apptList.count === 0
                                    text: "Nenhum compromisso. Clique em \"+ ADICIONAR COMPROMISSO\" ou peça pro " + (jarvisBackend.systemName || "Jarvis") + "."
                                    color: textMuted
                                    font.pixelSize: 11
                                }
                            }
                        }

                        // ============ CONTATOS ============
                        ColumnLayout {
                            visible: agendaPanel.agendaTab === 1
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            spacing: 8

                            RowLayout {
                                Layout.fillWidth: true
                                Text {
                                    Layout.fillWidth: true
                                    text: contactGrid.count + " contato(s)"
                                    color: textMuted; font.pixelSize: 9; font.letterSpacing: 1
                                }
                                JarvisButton {
                                    text: "+  ADICIONAR CONTATO"
                                    onClicked: contactEditor.openNew()
                                }
                            }

                            GridHeader {
                                HeaderCell { text: "NOME"; Layout.fillWidth: true }
                                HeaderCell { text: "TELEFONE"; Layout.preferredWidth: 140 }
                                HeaderCell { text: "E-MAIL"; Layout.preferredWidth: 200 }
                                HeaderCell { text: "ANIVERSÁRIO"; Layout.preferredWidth: 150 }
                                HeaderCell { text: "AÇÕES"; Layout.preferredWidth: 300 }
                            }

                            ListView {
                                id: contactGrid
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                clip: true
                                model: jarvisBackend.contacts
                                ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }

                                delegate: Rectangle {
                                    width: contactGrid.width
                                    height: 46
                                    color: index % 2 === 0 ? (window.isDark ? "#0A1526" : "#FFFFFF") : (window.isDark ? "#0B1A30" : "#F8FAFC")
                                    Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: window.isDark ? "#132A44" : "#E2E8F0" }

                                    RowLayout {
                                        anchors.fill: parent
                                        anchors.leftMargin: 14
                                        anchors.rightMargin: 12
                                        spacing: 12

                                        Text { Layout.fillWidth: true; text: modelData.name; color: textPrimary; font.pixelSize: 12; font.weight: Font.Medium; elide: Text.ElideRight }
                                        Text { Layout.preferredWidth: 140; text: modelData.phone || "—"; color: textMuted; font.pixelSize: 10; elide: Text.ElideRight }
                                        Text { Layout.preferredWidth: 200; text: modelData.email || "—"; color: textMuted; font.pixelSize: 10; elide: Text.ElideRight }
                                        Text {
                                            Layout.preferredWidth: 150
                                            text: modelData.birthdayLabel.length > 0 ? "🎂 " + modelData.birthdayLabel : (modelData.birthday || "—")
                                            color: modelData.birthdayLabel.length > 0 ? violet : textMuted
                                            font.pixelSize: 9; elide: Text.ElideRight
                                        }
                                        Row {
                                            Layout.preferredWidth: 300
                                            spacing: 5
                                            JarvisButton {
                                                visible: modelData.phone.length > 0
                                                variant: "success"
                                                text: "💬  WA"
                                                implicitHeight: 30; leftPadding: 10; rightPadding: 10; textSize: 9
                                                onClicked: jarvisBackend.openContactLink("whatsapp", modelData.phone)
                                            }
                                            JarvisButton {
                                                visible: modelData.phone.length > 0
                                                variant: "secondary"
                                                text: "⧉  COPIAR"
                                                implicitHeight: 30; leftPadding: 10; rightPadding: 10; textSize: 9
                                                onClicked: jarvisBackend.copyText(modelData.phone)
                                            }
                                            JarvisButton {
                                                visible: modelData.email.length > 0
                                                variant: "secondary"
                                                text: "✉  E-MAIL"
                                                implicitHeight: 30; leftPadding: 10; rightPadding: 10; textSize: 9
                                                onClicked: jarvisBackend.openContactLink("email", modelData.email)
                                            }
                                            JarvisButton {
                                                text: "✎"
                                                width: 32; height: 32
                                                textSize: 12
                                                ToolTip.visible: hovered
                                                ToolTip.text: "Editar contato"
                                                ToolTip.delay: 300
                                                onClicked: contactEditor.openEdit(modelData)
                                            }
                                            JarvisButton {
                                                variant: "danger"
                                                text: "✕"
                                                width: 32; height: 32
                                                textSize: 12
                                                ToolTip.visible: hovered
                                                ToolTip.text: "Excluir contato"
                                                ToolTip.delay: 300
                                                onClicked: { agendaDelete.kind = "contact"; agendaDelete.pending = modelData; agendaDelete.open() }
                                            }
                                        }
                                    }
                                }

                                Text {
                                    anchors.centerIn: parent
                                    visible: contactGrid.count === 0
                                    text: "Nenhum contato ainda. Clique em \"+ ADICIONAR CONTATO\"."
                                    color: textMuted
                                    font.pixelSize: 11
                                }
                            }
                        }
                    }
                }

                // painel de Arquivos (explorador + busca + previa)
                Rectangle {
                    id: filesPanel
                    objectName: "filesPanel"
                    anchors.fill: parent
                    anchors.margins: 20
                    visible: jarvisBackend.currentView === "arquivos"
                    radius: 16
                    color: window.isDark ? "#070E1E" : "#FFFFFF"
                    border.color: window.isDark ? "#152A44" : "#CBD5E1"
                    property string selectedPath: ""
                    property bool selectedIsDir: false
                    property string selectedName: ""

                    Component.onCompleted: if (jarvisBackend.fileEntries.length === 0) jarvisBackend.openFolder(jarvisBackend.filesPath)
                    Connections {
                        target: jarvisBackend
                        function onViewChanged() {
                            if (jarvisBackend.currentView === "arquivos" && jarvisBackend.fileEntries.length === 0)
                                jarvisBackend.openFolder(jarvisBackend.filesPath)
                        }
                        function onFilesChanged() { filesPanel.selectedPath = "" }
                    }

                    function glyphFor(kind) {
                        var m = {"folder": "📁", "image": "🖼", "text": "📄", "code": "⟨⟩",
                                 "pdf": "📕", "archive": "🗜", "audio": "♪", "video": "▶", "other": "•"}
                        return m[kind] || "•"
                    }

                    RowLayout {
                        anchors.fill: parent
                        anchors.margins: 20
                        spacing: 16

                        // ---- coluna esquerda: acesso rápido ----
                        ColumnLayout {
                            Layout.preferredWidth: 190
                            Layout.fillHeight: true
                            spacing: 6

                            Text { text: "ACESSO RÁPIDO"; color: textMuted; font.pixelSize: 8; font.letterSpacing: 1.4 }
                            Repeater {
                                model: jarvisBackend.quickAccess
                                delegate: Rectangle {
                                    Layout.fillWidth: true
                                    Layout.preferredHeight: 32
                                    radius: 8
                                    color: qaMouse.containsMouse ? (window.isDark ? "#0E1B30" : "#E0F2FE") : "transparent"
                                    Text {
                                        anchors.left: parent.left; anchors.leftMargin: 10
                                        anchors.verticalCenter: parent.verticalCenter
                                        text: modelData.label
                                        color: textPrimary; font.pixelSize: 10
                                        elide: Text.ElideRight
                                        width: parent.width - 20
                                    }
                                    MouseArea { id: qaMouse; anchors.fill: parent; hoverEnabled: true; onClicked: jarvisBackend.openFolder(modelData.path) }
                                }
                            }

                            Text {
                                text: "FAVORITOS"
                                color: textMuted; font.pixelSize: 8; font.letterSpacing: 1.4
                                Layout.topMargin: 10
                                visible: jarvisBackend.fileFavorites.length > 0
                            }
                            Repeater {
                                model: jarvisBackend.fileFavorites
                                delegate: Rectangle {
                                    Layout.fillWidth: true
                                    Layout.preferredHeight: 30
                                    radius: 8
                                    color: favMouse.containsMouse ? (window.isDark ? "#0E1B30" : "#E0F2FE") : "transparent"
                                    Text {
                                        anchors.left: parent.left; anchors.leftMargin: 10
                                        anchors.verticalCenter: parent.verticalCenter
                                        text: "★ " + modelData.label
                                        color: amber; font.pixelSize: 10
                                        elide: Text.ElideRight; width: parent.width - 20
                                    }
                                    MouseArea { id: favMouse; anchors.fill: parent; hoverEnabled: true; onClicked: jarvisBackend.openFolder(modelData.path) }
                                }
                            }
                            Item { Layout.fillHeight: true }
                        }

                        Rectangle { Layout.preferredWidth: 1; Layout.fillHeight: true; color: window.isDark ? "#152A44" : "#CBD5E1" }

                        // ---- coluna direita: barra + grid + seleção ----
                        ColumnLayout {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            spacing: 10

                            RowLayout {
                                Layout.fillWidth: true
                                Column {
                                    spacing: 3
                                    Text { text: "ARQUIVOS"; color: textPrimary; font.pixelSize: 17; font.weight: Font.DemiBold; font.letterSpacing: 2 }
                                    Text { text: "Explorar, buscar e pré-visualizar (somente leitura)."; color: textMuted; font.pixelSize: 10 }
                                }
                                Item { Layout.fillWidth: true }
                            }

                            // barra de navegação
                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 8
                                JarvisButton {
                                    text: "↑  SUBIR"
                                    enabled: jarvisBackend.filesParent.length > 0 && !jarvisBackend.filesSearchActive
                                    implicitHeight: 34; leftPadding: 10; rightPadding: 10; textSize: 9
                                    onClicked: jarvisBackend.filesGoUp()
                                }
                                JarvisButton {
                                    text: "⌂  HOME"
                                    implicitHeight: 34; leftPadding: 10; rightPadding: 10; textSize: 9
                                    onClicked: jarvisBackend.filesGoHome()
                                }
                                Rectangle {
                                    Layout.fillWidth: true
                                    Layout.preferredHeight: 34
                                    radius: 8
                                    color: window.isDark ? "#0A1526" : "#F8FAFC"
                                    border.color: window.isDark ? "#23435E" : "#CBD5E1"
                                    Text {
                                        anchors.fill: parent
                                        anchors.leftMargin: 12
                                        anchors.rightMargin: 12
                                        verticalAlignment: Text.AlignVCenter
                                        text: jarvisBackend.filesSearchActive ? ("Busca: \"" + fileSearch.text + "\"") : jarvisBackend.filesPath
                                        color: textMuted; font.pixelSize: 10
                                        elide: Text.ElideLeft
                                    }
                                }
                                JarvisButton {
                                    variant: "secondary"
                                    text: "📂  ABRIR NO EXPLORER"
                                    implicitHeight: 34; leftPadding: 12; rightPadding: 12; textSize: 8
                                    onClicked: jarvisBackend.revealInExplorer(jarvisBackend.filesPath)
                                }
                            }

                            // busca
                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 8
                                Rectangle {
                                    Layout.fillWidth: true
                                    Layout.preferredHeight: 34
                                    radius: 8
                                    color: window.isDark ? "#0D1D33" : "#FFFFFF"
                                    border.color: fileSearch.activeFocus ? cyan : (window.isDark ? "#23435E" : "#CBD5E1")
                                    TextInput {
                                        id: fileSearch
                                        anchors.fill: parent
                                        anchors.leftMargin: 12
                                        anchors.rightMargin: 12
                                        verticalAlignment: TextInput.AlignVCenter
                                        color: textPrimary
                                        font.pixelSize: 11
                                        clip: true
                                        onAccepted: jarvisBackend.searchFiles(text, fileContentToggle.checked)
                                        Text {
                                            anchors.fill: parent
                                            verticalAlignment: Text.AlignVCenter
                                            visible: parent.text.length === 0
                                            text: fileContentToggle.checked ? "Procurar texto dentro dos arquivos..." : "Procurar por nome nesta pasta e subpastas..."
                                            color: window.isDark ? "#526D83" : "#94A3B8"; font.pixelSize: 11
                                        }
                                    }
                                }
                                Button {
                                    id: fileContentToggle
                                    checkable: true
                                    text: "📄  CONTEUDO"
                                    implicitHeight: 34
                                    leftPadding: 12; rightPadding: 12
                                    background: Rectangle { radius: 8; color: parent.checked ? (window.isDark ? "#123049" : "#E0F2FE") : (window.isDark ? "#10293D" : "#F1F5F9"); border.color: parent.checked ? cyan : (window.isDark ? "#2A4C63" : "#CBD5E1"); opacity: parent.down ? 0.75 : 1 }
                                    contentItem: Text { text: parent.text; color: parent.checked ? cyan : textMuted; font.pixelSize: 8; font.weight: Font.DemiBold; font.letterSpacing: 1; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                                }
                                JarvisButton {
                                    text: jarvisBackend.filesBusy ? "..." : "🔍  BUSCAR"
                                    enabled: !jarvisBackend.filesBusy
                                    implicitHeight: 34; leftPadding: 12; rightPadding: 12; textSize: 9
                                    onClicked: jarvisBackend.searchFiles(fileSearch.text, fileContentToggle.checked)
                                }
                                JarvisButton {
                                    variant: "danger"
                                    visible: jarvisBackend.filesSearchActive
                                    text: "✕  LIMPAR"
                                    implicitHeight: 34; leftPadding: 12; rightPadding: 12; textSize: 9
                                    onClicked: { fileSearch.text = ""; jarvisBackend.openFolder(jarvisBackend.filesPath) }
                                }
                            }

                            Text {
                                visible: jarvisBackend.filesError.length > 0
                                Layout.fillWidth: true
                                text: jarvisBackend.filesError
                                color: amber; font.pixelSize: 9; wrapMode: Text.Wrap
                            }

                            // cabecalho do grid
                            Rectangle {
                                Layout.fillWidth: true
                                Layout.preferredHeight: 28
                                radius: 6
                                color: window.isDark ? "#0A1526" : "#F1F5F9"
                                RowLayout {
                                    anchors.fill: parent
                                    anchors.leftMargin: 14
                                    anchors.rightMargin: 12
                                    spacing: 12
                                    Text { text: "NOME"; color: textMuted; font.pixelSize: 8; font.weight: Font.DemiBold; font.letterSpacing: 1.2; Layout.fillWidth: true }
                                    Text { text: jarvisBackend.filesSearchActive ? "ONDE / TRECHO" : "MODIFICADO"; color: textMuted; font.pixelSize: 8; font.weight: Font.DemiBold; font.letterSpacing: 1.2; Layout.preferredWidth: 220 }
                                    Text { text: "TAMANHO"; color: textMuted; font.pixelSize: 8; font.weight: Font.DemiBold; font.letterSpacing: 1.2; Layout.preferredWidth: 90 }
                                }
                            }

                            ListView {
                                id: fileList
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                clip: true
                                model: jarvisBackend.fileEntries
                                ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }

                                delegate: Rectangle {
                                    width: fileList.width
                                    height: 40
                                    color: filesPanel.selectedPath === modelData.path ? (window.isDark ? "#123049" : "#E0F2FE")
                                           : (index % 2 === 0 ? (window.isDark ? "#0A1526" : "#FFFFFF") : (window.isDark ? "#0B1A30" : "#F8FAFC"))
                                    Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: window.isDark ? "#132A44" : "#E2E8F0" }

                                    RowLayout {
                                        anchors.fill: parent
                                        anchors.leftMargin: 14
                                        anchors.rightMargin: 12
                                        spacing: 12
                                        Row {
                                            Layout.fillWidth: true
                                            spacing: 9
                                            Text { text: filesPanel.glyphFor(modelData.kind); font.pixelSize: 13; anchors.verticalCenter: parent.verticalCenter }
                                            Text {
                                                anchors.verticalCenter: parent.verticalCenter
                                                text: modelData.name
                                                color: modelData.isDir ? cyan : textPrimary
                                                font.pixelSize: 11
                                                font.weight: modelData.isDir ? Font.DemiBold : Font.Normal
                                                elide: Text.ElideRight
                                                width: fileList.width - 380
                                            }
                                        }
                                        Text { text: modelData.modified || "—"; color: textMuted; font.pixelSize: 9; Layout.preferredWidth: 220; elide: Text.ElideRight }
                                        Text { text: modelData.sizeText || (modelData.isDir ? "pasta" : "—"); color: textMuted; font.pixelSize: 9; Layout.preferredWidth: 90 }
                                    }

                                    MouseArea {
                                        anchors.fill: parent
                                        onClicked: {
                                            filesPanel.selectedPath = modelData.path
                                            filesPanel.selectedIsDir = modelData.isDir
                                            filesPanel.selectedName = modelData.name
                                        }
                                        onDoubleClicked: {
                                            if (modelData.isDir) jarvisBackend.openFolder(modelData.path)
                                            else jarvisBackend.openFile(modelData.path)
                                        }
                                    }
                                }

                                Text {
                                    anchors.centerIn: parent
                                    visible: fileList.count === 0 && !jarvisBackend.filesBusy
                                    text: jarvisBackend.filesSearchActive ? "Nada encontrado." : "Pasta vazia."
                                    color: textMuted; font.pixelSize: 11
                                }
                                Text {
                                    anchors.centerIn: parent
                                    visible: jarvisBackend.filesBusy
                                    text: "Procurando..."
                                    color: cyan; font.pixelSize: 11
                                }
                            }

                            // barra de seleção
                            Rectangle {
                                Layout.fillWidth: true
                                Layout.preferredHeight: filesPanel.selectedPath.length > 0 ? 52 : 0
                                visible: filesPanel.selectedPath.length > 0
                                radius: 10
                                color: window.isDark ? "#0A1730" : "#F8FAFC"
                                border.color: window.isDark ? "#1B355A" : "#CBD5E1"
                                clip: true
                                RowLayout {
                                    anchors.fill: parent
                                    anchors.leftMargin: 14
                                    anchors.rightMargin: 12
                                    spacing: 10
                                    Text {
                                        Layout.fillWidth: true
                                        text: filesPanel.selectedName
                                        color: textPrimary; font.pixelSize: 11; font.weight: Font.DemiBold
                                        elide: Text.ElideMiddle
                                    }
                                    JarvisButton {
                                        text: filesPanel.selectedIsDir ? "📂  ABRIR" : "▶  ABRIR"
                                        implicitHeight: 34; leftPadding: 12; rightPadding: 12; textSize: 9
                                        onClicked: filesPanel.selectedIsDir ? jarvisBackend.openFolder(filesPanel.selectedPath) : jarvisBackend.openFile(filesPanel.selectedPath)
                                    }
                                    JarvisButton {
                                        variant: "secondary"
                                        visible: !filesPanel.selectedIsDir
                                        text: "👁  PRÉVIA"
                                        implicitHeight: 34; leftPadding: 12; rightPadding: 12; textSize: 9
                                        onClicked: filePreview.show(filesPanel.selectedPath, filesPanel.selectedName)
                                    }
                                    JarvisButton {
                                        visible: !filesPanel.selectedIsDir && filesPanel.selectedPath.toLowerCase().indexOf(".pdf") !== -1
                                        text: "✏  EDITAR PDF"
                                        implicitHeight: 34; leftPadding: 12; rightPadding: 12; textSize: 9
                                        onClicked: pdfEditorDialog.openFor(filesPanel.selectedPath)
                                    }
                                    JarvisButton {
                                        variant: "amber"
                                        visible: filesPanel.selectedIsDir
                                        text: "★  FAVORITAR"
                                        implicitHeight: 34; leftPadding: 12; rightPadding: 12; textSize: 9
                                        onClicked: jarvisBackend.toggleFileFavorite(filesPanel.selectedPath)
                                    }
                                    JarvisButton {
                                        id: jBtn
                                        text: "🤖  PEDIR PRO JARVIS"
                                        implicitHeight: 34; leftPadding: 12; rightPadding: 12; textSize: 9
                                        variant: "secondary"
                                        onClicked: jarvisBackend.askJarvisAboutFile(filesPanel.selectedPath)
                                    }
                                }
                            }
                        }
                    }
                }

                // painel de Análises (caixa de ferramentas)
                Rectangle {
                    id: toolboxPanel
                    objectName: "toolboxPanel"
                    anchors.fill: parent
                    anchors.margins: 20
                    visible: jarvisBackend.currentView === "analises"
                    radius: 16
                    color: window.isDark ? "#070E1E" : "#FFFFFF"
                    border.color: window.isDark ? "#152A44" : "#CBD5E1"

                    readonly property var categories: [
                        {"key": "documentos", "label": "DOCUMENTOS"},
                        {"key": "imagens", "label": "IMAGENS"},
                        {"key": "dados", "label": "TEXTO & DADOS"},
                        {"key": "ia", "label": "COM INTELIGÊNCIA ARTIFICIAL"}
                    ]
                    function utilsOf(cat) {
                        return jarvisBackend.toolboxUtilities.filter(function(u) { return u.category === cat })
                    }

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 22
                        spacing: 12

                        Column {
                            spacing: 3
                            Text { text: "ANÁLISES  //  FERRAMENTAS"; color: textPrimary; font.pixelSize: 17; font.weight: Font.DemiBold; font.letterSpacing: 2 }
                            Text { text: "Converter, extrair, resumir e mais. Tudo local; a saída vai num arquivo novo ao lado do original."; color: textMuted; font.pixelSize: 10 }
                        }

                        ScrollView {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            contentWidth: availableWidth
                            clip: true

                            ColumnLayout {
                                width: parent.width
                                spacing: 16

                                Repeater {
                                    model: toolboxPanel.categories
                                    delegate: ColumnLayout {
                                        Layout.fillWidth: true
                                        spacing: 8
                                        Text { text: modelData.label; color: cyan; font.pixelSize: 10; font.weight: Font.DemiBold; font.letterSpacing: 1.6 }
                                        Flow {
                                            Layout.fillWidth: true
                                            spacing: 10
                                            Repeater {
                                                model: toolboxPanel.utilsOf(modelData.key)
                                                delegate: Rectangle {
                                                    width: 244
                                                    height: 92
                                                    radius: 12
                                                    color: cardMouse.containsMouse && modelData.available
                                                           ? (window.isDark ? "#0E2036" : "#E0F2FE")
                                                           : (window.isDark ? "#0A1526" : "#F8FAFC")
                                                    border.color: modelData.available ? (window.isDark ? "#1B355A" : "#CBD5E1") : "#3A2A10"
                                                    opacity: modelData.available ? 1 : 0.7

                                                    ColumnLayout {
                                                        anchors.fill: parent
                                                        anchors.margins: 13
                                                        spacing: 4
                                                        RowLayout {
                                                            Layout.fillWidth: true
                                                            Text { text: modelData.name; color: textPrimary; font.pixelSize: 12; font.weight: Font.DemiBold; Layout.fillWidth: true; elide: Text.ElideRight }
                                                            Text { visible: modelData.ai; text: "IA"; color: violet; font.pixelSize: 8; font.weight: Font.DemiBold }
                                                        }
                                                        Text {
                                                            Layout.fillWidth: true
                                                            text: modelData.available ? modelData.description : "Precisa do extra .[tools] — clique para ver como instalar."
                                                            color: textMuted; font.pixelSize: 9; wrapMode: Text.Wrap; maximumLineCount: 3; elide: Text.ElideRight
                                                        }
                                                    }
                                                    MouseArea {
                                                        id: cardMouse
                                                        anchors.fill: parent
                                                        hoverEnabled: true
                                                        onClicked: {
                                                            if (modelData.id === "pdf_editor") {
                                                                pdfEditorDialog.openFor(null)
                                                            } else {
                                                                utilityDialog.openFor(modelData)
                                                            }
                                                        }
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }

                // painel do Sistema (painel de controle)
                Rectangle {
                    id: sistemaPanel
                    objectName: "sistemaPanel"
                    anchors.fill: parent
                    anchors.margins: 20
                    visible: jarvisBackend.currentView === "sistema"
                    radius: 16
                    color: window.isDark ? "#070E1E" : "#FFFFFF"
                    border.color: window.isDark ? "#152A44" : "#CBD5E1"
                    property int sysTab: 0
                    property string procSort: "cpu"

                    Component.onCompleted: sistemaPanel.loadTab()
                    Connections {
                        target: jarvisBackend
                        function onViewChanged() {
                            if (jarvisBackend.currentView === "sistema") sistemaPanel.loadTab()
                        }
                    }
                    function loadTab() {
                        if (sysTab === 0 && !jarvisBackend.systemSpecs.available) jarvisBackend.refreshSpecs()
                        else if (sysTab === 1 && jarvisBackend.processList.length === 0) jarvisBackend.refreshProcesses(procSort)
                        else if (sysTab === 2 && (jarvisBackend.diskInfo.volumes || []).length === 0) jarvisBackend.refreshDisks()
                        else if (sysTab === 3 && !jarvisBackend.powerInfo.plans) jarvisBackend.refreshSpecs()
                    }

                    component SpecTable : Rectangle {
                        id: specRoot
                        Layout.fillWidth: true
                        radius: 12
                        color: window.isDark ? "#0A1526" : "#F8FAFC"
                        border.color: window.isDark ? "#1B355A" : "#CBD5E1"
                        property string title: ""
                        property var rows: []
                        implicitHeight: specCol.height + 28
                        ColumnLayout {
                            id: specCol
                            x: 14
                            y: 14
                            width: parent.width - 28
                            spacing: 7
                            Text { text: specRoot.title; color: cyan; font.pixelSize: 9; font.weight: Font.DemiBold; font.letterSpacing: 1.4 }
                            Repeater {
                                model: specRoot.rows
                                delegate: RowLayout {
                                    Layout.fillWidth: true
                                    Text { text: modelData.k; color: textMuted; font.pixelSize: 10; Layout.preferredWidth: 180 }
                                    Text { text: modelData.v; color: textPrimary; font.pixelSize: 10; Layout.fillWidth: true; wrapMode: Text.Wrap }
                                }
                            }
                            Text {
                                visible: (specRoot.rows || []).length === 0
                                text: jarvisBackend.systemBusy ? "Lendo..." : "sem dados"
                                color: textMuted; font.pixelSize: 9
                            }
                        }
                    }

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 22
                        spacing: 12

                        RowLayout {
                            Layout.fillWidth: true
                            Column {
                                spacing: 3
                                Text { text: "SISTEMA  //  PAINEL DE CONTROLE"; color: textPrimary; font.pixelSize: 17; font.weight: Font.DemiBold; font.letterSpacing: 2 }
                                Text { text: "Especificações, processos, discos, energia e manutenção."; color: textMuted; font.pixelSize: 10 }
                            }
                            Item { Layout.fillWidth: true }
                            Text {
                                visible: jarvisBackend.systemBusy || jarvisBackend.processBusy
                                text: "carregando..."; color: cyan; font.pixelSize: 9
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 4
                            Repeater {
                                model: [
                                    {"t": "ESPECIFICAÇÕES", "i": 0},
                                    {"t": "PROCESSOS", "i": 1},
                                    {"t": "DISCOS", "i": 2},
                                    {"t": "ENERGIA", "i": 3},
                                    {"t": "AÇÕES RÁPIDAS", "i": 4}
                                ]
                                delegate: Rectangle {
                                    Layout.preferredWidth: 150
                                    Layout.preferredHeight: 36
                                    color: "transparent"
                                    readonly property bool sel: sistemaPanel.sysTab === modelData.i
                                    Text { anchors.centerIn: parent; text: modelData.t; color: parent.sel ? cyan : textMuted; font.pixelSize: 9; font.weight: Font.DemiBold; font.letterSpacing: 1 }
                                    Rectangle { anchors.bottom: parent.bottom; anchors.left: parent.left; anchors.right: parent.right; height: 2; color: parent.sel ? cyan : (window.isDark ? "#1E3A55" : "#E2E8F0") }
                                    MouseArea { anchors.fill: parent; onClicked: { sistemaPanel.sysTab = modelData.i; sistemaPanel.loadTab() } }
                                }
                            }
                            Item { Layout.fillWidth: true }
                        }

                        // ===== ESPECIFICACOES =====
                        ScrollView {
                            visible: sistemaPanel.sysTab === 0
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            contentWidth: availableWidth
                            clip: true
                            ColumnLayout {
                                width: parent.width
                                spacing: 12
                                SpecTable { title: "HARDWARE"; rows: jarvisBackend.systemSpecs.hardware || [] }
                                SpecTable { title: "PLACA DE VIDEO"; rows: jarvisBackend.systemSpecs.gpu || []; visible: (jarvisBackend.systemSpecs.gpu || []).length > 0 }
                                SpecTable { title: "SISTEMA"; rows: jarvisBackend.systemSpecs.system || [] }
                                Rectangle {
                                    id: jiRoot
                                    Layout.fillWidth: true
                                    radius: 12
                                    color: window.isDark ? "#0A1526" : "#F8FAFC"
                                    border.color: window.isDark ? "#1B355A" : "#CBD5E1"
                                    implicitHeight: jiCol.height + 28
                                    ColumnLayout {
                                        id: jiCol
                                        x: 14
                                        y: 14
                                        width: parent.width - 28
                                        spacing: 7
                                        Text { text: jarvisBackend.systemName ? jarvisBackend.systemName.toUpperCase() : "JARVIS"; color: violet; font.pixelSize: 9; font.weight: Font.DemiBold; font.letterSpacing: 1.4 }
                                        Repeater {
                                            model: [
                                                ["Versão", jarvisBackend.jarvisInfo.version],
                                                ["Provedor / modelo", jarvisBackend.jarvisInfo.provider + " / " + jarvisBackend.jarvisInfo.model],
                                                ["Pasta de dados", jarvisBackend.jarvisInfo.dataDir],
                                                ["Banco de dados", jarvisBackend.jarvisInfo.dbSize],
                                                ["Conversas / mensagens", jarvisBackend.jarvisInfo.conversations + " / " + jarvisBackend.jarvisInfo.messages],
                                                ["Rotinas / compromissos / contatos", jarvisBackend.jarvisInfo.routines + " / " + jarvisBackend.jarvisInfo.appointments + " / " + jarvisBackend.jarvisInfo.contacts]
                                            ]
                                            delegate: RowLayout {
                                                Layout.fillWidth: true
                                                Text { text: modelData[0]; color: textMuted; font.pixelSize: 10; Layout.preferredWidth: 170 }
                                                Text { text: "" + modelData[1]; color: textPrimary; font.pixelSize: 10; Layout.fillWidth: true; wrapMode: Text.Wrap }
                                            }
                                        }
                                        JarvisButton {
                                            variant: "secondary"
                                            text: "📂  ABRIR PASTA DE DADOS"
                                            implicitHeight: 32; leftPadding: 12; rightPadding: 12; textSize: 8
                                            onClicked: jarvisBackend.revealInExplorer(jarvisBackend.jarvisInfo.dataDir)
                                        }
                                    }
                                }
                                JarvisButton {
                                    Layout.alignment: Qt.AlignLeft
                                    text: "↻  ATUALIZAR"
                                    onClicked: jarvisBackend.refreshSpecs()
                                }
                            }
                        }

                        // ===== PROCESSOS =====
                        ColumnLayout {
                            visible: sistemaPanel.sysTab === 1
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            spacing: 8
                            RowLayout {
                                Layout.fillWidth: true
                                Text { text: jarvisBackend.processList.length + " processo(s) - mais pesados no topo"; color: textMuted; font.pixelSize: 9; Layout.fillWidth: true }
                                Repeater {
                                    model: [{"t": "POR CPU", "v": "cpu"}, {"t": "POR MEMÓRIA", "v": "memory"}]
                                    delegate: Button {
                                        text: (sistemaPanel.procSort === modelData.v ? "●  " : "") + modelData.t
                                        onClicked: { sistemaPanel.procSort = modelData.v; jarvisBackend.refreshProcesses(modelData.v) }
                                        implicitHeight: 32
                                        leftPadding: 11; rightPadding: 11
                                        background: Rectangle { radius: 7; color: sistemaPanel.procSort === modelData.v ? (window.isDark ? "#123049" : "#E0F2FE") : (window.isDark ? "#10293D" : "#F1F5F9"); border.color: sistemaPanel.procSort === modelData.v ? cyan : (window.isDark ? "#2A4C63" : "#CBD5E1"); opacity: parent.down ? 0.75 : 1 }
                                        contentItem: Text { text: parent.text; color: sistemaPanel.procSort === modelData.v ? cyan : textMuted; font.pixelSize: 8; font.weight: Font.DemiBold; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                                    }
                                }
                                JarvisButton {
                                    text: "↻"
                                    implicitHeight: 32; leftPadding: 10; rightPadding: 10; textSize: 13
                                    onClicked: jarvisBackend.refreshProcesses(sistemaPanel.procSort)
                                }
                            }
                            Rectangle {
                                Layout.fillWidth: true; Layout.preferredHeight: 26; radius: 6; color: window.isDark ? "#0A1526" : "#F1F5F9"
                                RowLayout {
                                    anchors.fill: parent; anchors.leftMargin: 14; anchors.rightMargin: 12; spacing: 12
                                    Text { text: "PROCESSO"; color: textMuted; font.pixelSize: 8; font.weight: Font.DemiBold; Layout.fillWidth: true }
                                    Text { text: "PID"; color: textMuted; font.pixelSize: 8; font.weight: Font.DemiBold; Layout.preferredWidth: 70 }
                                    Text { text: "USUÁRIO"; color: textMuted; font.pixelSize: 8; font.weight: Font.DemiBold; Layout.preferredWidth: 100 }
                                    Text { text: "CPU"; color: textMuted; font.pixelSize: 8; font.weight: Font.DemiBold; Layout.preferredWidth: 70 }
                                    Text { text: "MEMÓRIA"; color: textMuted; font.pixelSize: 8; font.weight: Font.DemiBold; Layout.preferredWidth: 90 }
                                    Text { text: ""; Layout.preferredWidth: 80 }
                                }
                            }
                            ListView {
                                id: procList
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                clip: true
                                model: jarvisBackend.processList
                                ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }
                                delegate: Rectangle {
                                    width: procList.width; height: 34
                                    color: index % 2 === 0 ? (window.isDark ? "#0A1526" : "#FFFFFF") : (window.isDark ? "#0B1A30" : "#F8FAFC")
                                    RowLayout {
                                        anchors.fill: parent; anchors.leftMargin: 14; anchors.rightMargin: 12; spacing: 12
                                        Text { text: modelData.name; color: textPrimary; font.pixelSize: 10; Layout.fillWidth: true; elide: Text.ElideRight }
                                        Text { text: "" + modelData.pid; color: textMuted; font.pixelSize: 9; Layout.preferredWidth: 70 }
                                        Text { text: modelData.user || "-"; color: textMuted; font.pixelSize: 9; Layout.preferredWidth: 100; elide: Text.ElideRight }
                                        Text { text: modelData.cpuText; color: modelData.cpu > 20 ? amber : textMuted; font.pixelSize: 9; Layout.preferredWidth: 70 }
                                        Text { text: modelData.memText; color: textMuted; font.pixelSize: 9; Layout.preferredWidth: 90 }
                                        JarvisButton {
                                            variant: "danger"
                                            Layout.preferredWidth: 80
                                            enabled: !modelData.protected
                                            text: modelData.protected ? "protegido" : "🛑  FINALIZAR"
                                            implicitHeight: 28; leftPadding: 4; rightPadding: 4; textSize: 8
                                            onClicked: { sysConfirm.open2("Finalizar \"" + modelData.name + "\" (PID " + modelData.pid + ")?", function() { jarvisBackend.killProcess(modelData.pid, sistemaPanel.procSort) }) }
                                        }
                                    }
                                }
                                Text { anchors.centerIn: parent; visible: procList.count === 0; text: jarvisBackend.processBusy ? "Lendo processos..." : "Sem dados."; color: textMuted; font.pixelSize: 11 }
                            }
                        }

                        // ===== DISCOS =====
                        ColumnLayout {
                            visible: sistemaPanel.sysTab === 2
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            spacing: 12
                            Text {
                                visible: (jarvisBackend.diskInfo.volumes || []).length === 0
                                text: jarvisBackend.systemBusy ? "Lendo discos..." : "Sem dados."
                                color: textMuted; font.pixelSize: 10
                            }
                            Repeater {
                                model: jarvisBackend.diskInfo.volumes || []
                                delegate: Rectangle {
                                    Layout.fillWidth: true
                                    Layout.preferredHeight: 70
                                    radius: 12; color: window.isDark ? "#0A1526" : "#F8FAFC"; border.color: window.isDark ? "#1B355A" : "#CBD5E1"
                                    ColumnLayout {
                                        anchors.fill: parent; anchors.margins: 14; spacing: 6
                                        RowLayout {
                                            Layout.fillWidth: true
                                            Text { text: modelData.device + "  " + modelData.fstype; color: textPrimary; font.pixelSize: 12; font.weight: Font.DemiBold; Layout.fillWidth: true }
                                            Text { text: modelData.usedText + " usados de " + modelData.totalText + "  (" + modelData.freeText + " livres)"; color: textMuted; font.pixelSize: 10 }
                                        }
                                        Rectangle {
                                            Layout.fillWidth: true; height: 8; radius: 4; color: window.isDark ? "#122840" : "#E2E8F0"
                                            Rectangle {
                                                width: parent.width * Math.min(100, modelData.percent) / 100
                                                height: parent.height; radius: 4
                                                color: modelData.percent > 90 ? "#FF6B8A" : (modelData.percent > 75 ? amber : cyan)
                                            }
                                        }
                                    }
                                }
                            }
                            Rectangle {
                                Layout.fillWidth: true
                                Layout.preferredHeight: 96
                                radius: 12; color: window.isDark ? "#0A1526" : "#F8FAFC"; border.color: window.isDark ? "#1B355A" : "#CBD5E1"
                                ColumnLayout {
                                    anchors.fill: parent; anchors.margins: 14; spacing: 8
                                    Text { text: "LIMPEZA"; color: cyan; font.pixelSize: 9; font.weight: Font.DemiBold; font.letterSpacing: 1.4 }
                                    RowLayout {
                                        Layout.fillWidth: true
                                        spacing: 12
                                        JarvisButton {
                                            text: "🗑  LIMPAR TEMP  (" + ((jarvisBackend.diskInfo.temp || {}).sizeText || "--") + ")"
                                            textSize: 9
                                            onClicked: sysConfirm.open2("Apagar os arquivos temporários (%TEMP%)? Os que estiverem em uso serão ignorados.", function() { jarvisBackend.cleanTemp() })
                                        }
                                        JarvisButton {
                                            variant: "danger"
                                            text: "🗑  ESVAZIAR LIXEIRA  (" + ((jarvisBackend.diskInfo.recycle || {}).sizeText || "--") + ")"
                                            textSize: 9
                                            onClicked: sysConfirm.open2("Esvaziar a Lixeira do Windows? Isso apaga tudo de forma permanente.", function() { jarvisBackend.emptyRecycleBin() })
                                        }
                                        JarvisButton {
                                            variant: "secondary"
                                            text: "↻"
                                            leftPadding: 10; rightPadding: 10; textSize: 13
                                            onClicked: jarvisBackend.refreshDisks()
                                        }
                                        Item { Layout.fillWidth: true }
                                    }
                                }
                            }
                            Item { Layout.fillHeight: true }
                        }

                        // ===== ENERGIA =====
                        ColumnLayout {
                            visible: sistemaPanel.sysTab === 3
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            spacing: 12
                            Rectangle {
                                Layout.fillWidth: true
                                Layout.preferredHeight: 110
                                radius: 12; color: window.isDark ? "#0A1526" : "#F8FAFC"; border.color: window.isDark ? "#1B355A" : "#CBD5E1"
                                visible: jarvisBackend.powerInfo.hasBattery === true
                                RowLayout {
                                    anchors.fill: parent; anchors.margins: 18; spacing: 20
                                    Text {
                                        text: (jarvisBackend.powerInfo.percent || 0) + "%"
                                        color: (jarvisBackend.powerInfo.percent || 0) < 20 ? "#FF6B8A" : cyan
                                        font.pixelSize: 40; font.weight: Font.Light
                                    }
                                    Column {
                                        Layout.fillWidth: true
                                        spacing: 4
                                        Text { text: "BATERIA"; color: textMuted; font.pixelSize: 8; font.letterSpacing: 1.4 }
                                        Text { text: jarvisBackend.powerInfo.plugged ? "Na tomada" : "Na bateria"; color: textPrimary; font.pixelSize: 13; font.weight: Font.DemiBold }
                                        Text { text: "Estimativa: " + (jarvisBackend.powerInfo.remaining || "--"); color: textMuted; font.pixelSize: 10 }
                                    }
                                }
                            }
                            Rectangle {
                                Layout.fillWidth: true
                                Layout.preferredHeight: 96
                                radius: 12; color: window.isDark ? "#0A1526" : "#F8FAFC"; border.color: window.isDark ? "#1B355A" : "#CBD5E1"
                                ColumnLayout {
                                    anchors.fill: parent; anchors.margins: 16; spacing: 8
                                    Text { text: "PLANO DE ENERGIA"; color: cyan; font.pixelSize: 9; font.weight: Font.DemiBold; font.letterSpacing: 1.4 }
                                    Flow {
                                        Layout.fillWidth: true
                                        spacing: 8
                                        Repeater {
                                            model: jarvisBackend.powerInfo.plans || []
                                            delegate: Button {
                                                text: (parent.active ? "●  " : "") + modelData.name
                                                readonly property bool active: (jarvisBackend.powerInfo.activePlan || "").toLowerCase() === modelData.guid.toLowerCase()
                                                onClicked: jarvisBackend.setPowerPlan(modelData.guid)
                                                implicitHeight: 36
                                                leftPadding: 14; rightPadding: 14
                                                background: Rectangle { radius: 8; color: parent.active ? (window.isDark ? "#123049" : "#E0F2FE") : (window.isDark ? "#10293D" : "#F1F5F9"); border.color: parent.active ? cyan : (window.isDark ? "#2A4C63" : "#CBD5E1"); opacity: parent.down ? 0.75 : 1 }
                                                contentItem: Text { text: parent.text; color: parent.active ? cyan : textMuted; font.pixelSize: 9; font.weight: Font.DemiBold; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                                            }
                                        }
                                    }
                                    Text {
                                        visible: (jarvisBackend.powerInfo.plans || []).length <= 1
                                        text: "Seu Windows expõe so um plano aqui. Ajuste fino do modo de energia fica em Configurações > Energia."
                                        color: textMuted; font.pixelSize: 9; wrapMode: Text.Wrap; Layout.fillWidth: true
                                    }
                                }
                            }
                            Item { Layout.fillHeight: true }
                        }

                        // ===== AÇÕES RÁPIDAS =====
                        Flow {
                            visible: sistemaPanel.sysTab === 4
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            spacing: 10
                            Repeater {
                                model: [
                                    {"t": "Limpar cache de DNS", "d": "Resolve problemas de sites que não abrem.", "a": "flush_dns"},
                                    {"t": "Reiniciar o Explorer", "d": "Barra de tarefas travada ou icones sumindo.", "a": "restart_explorer"},
                                    {"t": "Gerenciador de Tarefas", "d": "Abre o Gerenciador de Tarefas do Windows.", "a": "task_manager"},
                                    {"t": "Configurações do Windows", "d": "Abre o app de Configurações.", "a": "windows_settings"},
                                    {"t": "Painel de Controle", "d": "Abre o Painel de Controle clássico.", "a": "control_panel"},
                                    {"t": "Windows Update", "d": "Verificar atualizações do Windows.", "a": "windows_update"}
                                ]
                                delegate: Rectangle {
                                    width: 250; height: 88
                                    radius: 12
                                    color: qaMouse2.containsMouse ? (window.isDark ? "#0E2036" : "#E0F2FE") : (window.isDark ? "#0A1526" : "#F8FAFC")
                                    border.color: window.isDark ? "#1B355A" : "#CBD5E1"
                                    ColumnLayout {
                                        anchors.fill: parent; anchors.margins: 13; spacing: 4
                                        Text { text: modelData.t; color: textPrimary; font.pixelSize: 12; font.weight: Font.DemiBold }
                                        Text { text: modelData.d; color: textMuted; font.pixelSize: 9; wrapMode: Text.Wrap; Layout.fillWidth: true }
                                    }
                                    MouseArea { id: qaMouse2; anchors.fill: parent; hoverEnabled: true; onClicked: jarvisBackend.runQuickAction(modelData.a) }
                                }
                            }
                        }
                    }
                }

                // painel de Automação (Rotinas)
                Rectangle {
                    anchors.fill: parent
                    anchors.margins: 20
                    visible: jarvisBackend.currentView === "automacao"
                    radius: 16
                    color: window.isDark ? "#070E1E" : "#FFFFFF"
                    border.color: window.isDark ? "#152A44" : "#CBD5E1"

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 22
                        spacing: 14

                        RowLayout {
                            Layout.fillWidth: true
                            Column {
                                spacing: 3
                                Text {
                                    text: "AUTOMAÇÃO  //  ROTINAS"
                                    color: textPrimary
                                    font.pixelSize: 17
                                    font.weight: Font.DemiBold
                                    font.letterSpacing: 2
                                }
                                Text {
                                    text: "Sequencias de ações. Dispare por aqui ou por voz: \"" + (jarvisBackend.systemName ? jarvisBackend.systemName.toLowerCase() : "jarvis") + ", rodar <nome>\"."
                                    color: textMuted
                                    font.pixelSize: 10
                                }
                            }
                            Item { Layout.fillWidth: true }
                            JarvisButton {
                                text: "+  NOVA ROTINA"
                                onClicked: routineEditor.openNew()
                            }
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            visible: !jarvisBackend.agentReadyForRoutines
                            Layout.preferredHeight: 40
                            radius: 9
                            color: window.isDark ? "#3A2A10" : "#FEF3C7"
                            border.color: amber
                            Text {
                                anchors.centerIn: parent
                                text: "O Agente está desligado — as rotinas so agem no PC com ele ligado (Configurações > Permissões)."
                                color: window.isDark ? "#F6D9A0" : "#92400E"
                                font.pixelSize: 9
                            }
                        }

                        ListView {
                            id: routineList
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            clip: true
                            spacing: 10
                            model: jarvisBackend.routines
                            ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }

                            delegate: Rectangle {
                                width: routineList.width
                                height: 116
                                radius: 12
                                color: window.isDark ? "#0A1730" : "#F8FAFC"
                                border.color: window.isDark ? "#1B355A" : "#CBD5E1"

                                ColumnLayout {
                                    anchors.fill: parent
                                    anchors.leftMargin: 16
                                    anchors.rightMargin: 12
                                    anchors.topMargin: 12
                                    anchors.bottomMargin: 10
                                    spacing: 8

                                    RowLayout {
                                        Layout.fillWidth: true
                                        spacing: 12

                                        Column {
                                            Layout.fillWidth: true
                                            spacing: 3
                                            Text {
                                                text: modelData.name
                                                color: textPrimary
                                                font.pixelSize: 13
                                                font.weight: Font.DemiBold
                                            }
                                            Text {
                                                text: (modelData.description && modelData.description.length > 0
                                                       ? modelData.description + "  ·  " : "")
                                                      + modelData.stepCount + " passo(s)"
                                                color: textMuted
                                                font.pixelSize: 10
                                                elide: Text.ElideRight
                                                width: routineList.width - 280
                                            }
                                        }

                                        JarvisButton {
                                            variant: "success"
                                            text: "▶  EXECUTAR"
                                            Layout.preferredHeight: 32
                                            Layout.alignment: Qt.AlignVCenter
                                            enabled: !jarvisBackend.busy
                                            leftPadding: 12; rightPadding: 12; textSize: 9
                                            onClicked: jarvisBackend.runRoutine(modelData.id)
                                        }
                                        JarvisButton {
                                            variant: "secondary"
                                            text: "✎  EDITAR"
                                            Layout.preferredHeight: 32
                                            Layout.alignment: Qt.AlignVCenter
                                            leftPadding: 10; rightPadding: 10; textSize: 9
                                            onClicked: routineEditor.openEdit(modelData)
                                        }
                                        JarvisButton {
                                            variant: "danger"
                                            Layout.preferredWidth: 32
                                            Layout.preferredHeight: 32
                                            Layout.alignment: Qt.AlignVCenter
                                            text: "✕"
                                            textSize: 12
                                            ToolTip.visible: hovered
                                            ToolTip.text: "Excluir rotina"
                                            ToolTip.delay: 300
                                            onClicked: { routineDelete.pending = modelData; routineDelete.open() }
                                        }
                                    }

                                    Rectangle { Layout.fillWidth: true; height: 1; color: window.isDark ? "#15305088" : "#E2E8F0" }

                                    RowLayout {
                                        Layout.fillWidth: true
                                        spacing: 10

                                        Text {
                                            text: "⏰"
                                            color: modelData.scheduleActive ? amber : "#3E5570"
                                            font.pixelSize: 12
                                        }
                                        Text {
                                            Layout.fillWidth: true
                                            text: modelData.scheduled ? modelData.scheduleText : "Sem agendamento"
                                            color: modelData.scheduleActive ? (window.isDark ? "#F6D9A0" : "#B45309") : textMuted
                                            font.pixelSize: 9
                                            elide: Text.ElideRight
                                        }
                                        JarvisButton {
                                            text: modelData.scheduled ? "⏰  ALTERAR" : "⏰  AGENDAR"
                                            implicitHeight: 30; leftPadding: 10; rightPadding: 10; textSize: 8
                                            onClicked: scheduleEditor.openFor(modelData)
                                        }
                                        JarvisButton {
                                            variant: "danger"
                                            visible: modelData.scheduled
                                            text: "✕  REMOVER"
                                            implicitHeight: 30; leftPadding: 10; rightPadding: 10; textSize: 8
                                            onClicked: jarvisBackend.clearSchedule(modelData.id)
                                        }
                                    }
                                }
                            }

                            Text {
                                anchors.centerIn: parent
                                visible: routineList.count === 0
                                text: "Nenhuma rotina ainda. Crie a primeira em \"+ NOVA ROTINA\"."
                                color: textMuted
                                font.pixelSize: 11
                            }
                        }
                    }
                }

                // painel de Comunicação e Agentes de IA
                Rectangle {
                    id: comunicacaoPanel
                    objectName: "comunicacaoPanel"
                    anchors.fill: parent
                    anchors.margins: 20
                    visible: jarvisBackend.currentView === "comunicacao"
                    radius: 16
                    color: window.isDark ? "#070E1E" : "#FFFFFF"
                    border.color: window.isDark ? "#152A44" : "#CBD5E1"

                    property int commMainTab: 0

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 22
                        spacing: 16

                        // Navegação Principal de Abas (Agente de IA / Comunicação)
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 12

                            Repeater {
                                model: [
                                    {"t": "🤖  Agente de IA", "i": 0},
                                    {"t": "💬  Comunicação", "i": 1}
                                ]
                                delegate: Button {
                                    width: 170
                                    height: 38
                                    text: (comunicacaoPanel.commMainTab === modelData.i ? "●  " : "") + modelData.t
                                    onClicked: comunicacaoPanel.commMainTab = modelData.i
                                    background: Rectangle {
                                        radius: 10
                                        color: comunicacaoPanel.commMainTab === modelData.i ? (window.isDark ? "#123049" : "#E0F2FE") : (parent.hovered ? (window.isDark ? "#0E1F33" : "#F1F5F9") : "transparent")
                                border.color: comunicacaoPanel.commMainTab === modelData.i ? cyan : (window.isDark ? "#25405A" : "#CBD5E1")
                                    }
                                    contentItem: Text {
                                        text: parent.text
                                        color: comunicacaoPanel.commMainTab === modelData.i ? cyan : textMuted
                                        horizontalAlignment: Text.AlignHCenter
                                        verticalAlignment: Text.AlignVCenter
                                        font.pixelSize: 11
                                        font.weight: Font.DemiBold
                                        font.letterSpacing: 1.1
                                    }
                                }
                            }

                            Item { Layout.fillWidth: true }
                        }

                        // ======================================================== ABA 0: AGENTE DE IA
                        ColumnLayout {
                            visible: comunicacaoPanel.commMainTab === 0
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            spacing: 16

                            // Header da Aba Agente de IA
                            RowLayout {
                                Layout.fillWidth: true
                                Column {
                                    spacing: 3
                                    Text {
                                        text: "AGENTES & AUTOMAÇÃO"
                                        color: green
                                        font.pixelSize: 9
                                        font.weight: Font.Bold
                                        font.letterSpacing: 1.5
                                    }
                                    Text {
                                        text: "Agentes de Inteligência Artificial"
                                        color: textPrimary
                                        font.pixelSize: 18
                                        font.weight: Font.DemiBold
                                        font.letterSpacing: 1.1
                                    }
                                    Text {
                                        text: "Crie e gerencie agentes inteligentes com modelos OpenAI, Anthropic, Gemini, Groq, OpenRouter, LM Studio e Ollama."
                                        color: textMuted
                                        font.pixelSize: 10
                                    }
                                }

                                Item { Layout.fillWidth: true }

                                JarvisButton {
                                    variant: "success"
                                    text: "+  Configurar Modelo"
                                    implicitHeight: 38
                                    leftPadding: 16; rightPadding: 16
                                    onClicked: agentEditorModal.openNew()
                                }
                            }

                            // Barra de Métricas dos Agentes
                            Rectangle {
                                Layout.fillWidth: true
                                Layout.preferredHeight: 64
                                radius: 12
                                color: window.isDark ? "#0A1526" : "#F8FAFC"
                                border.color: window.isDark ? "#183650" : "#CBD5E1"

                                RowLayout {
                                    anchors.fill: parent
                                    anchors.leftMargin: 20
                                    anchors.rightMargin: 20
                                    spacing: 20

                                    // Métrica 1: Total de Modelos Configurados
                                    Row {
                                        spacing: 12
                                        Rectangle {
                                            width: 36; height: 36; radius: 18
                                            color: window.isDark ? "#123049" : "#E0F2FE"
                                            anchors.verticalCenter: parent.verticalCenter
                                            Text { anchors.centerIn: parent; text: "🤖"; font.pixelSize: 15 }
                                        }
                                        Column {
                                            anchors.verticalCenter: parent.verticalCenter
                                            spacing: 2
                                            Text { text: "Modelos Configurados"; color: textMuted; font.pixelSize: 9 }
                                            Text {
                                                text: "" + (jarvisBackend.aiAgents ? jarvisBackend.aiAgents.length : 0)
                                                color: textPrimary
                                                font.pixelSize: 14
                                                font.weight: Font.Bold
                                            }
                                        }
                                    }

                                    Rectangle { width: 1; height: 30; color: window.isDark ? "#1C3650" : "#E2E8F0" }

                                    // Métrica 2: Provedores Suportados
                                    Row {
                                        spacing: 12
                                        Rectangle {
                                            width: 36; height: 36; radius: 18
                                            color: window.isDark ? "#0C2E20" : "#DCFCE7"
                                            anchors.verticalCenter: parent.verticalCenter
                                            Text { anchors.centerIn: parent; text: "⚡"; font.pixelSize: 15 }
                                        }
                                        Column {
                                            anchors.verticalCenter: parent.verticalCenter
                                            spacing: 2
                                            Text { text: "Provedores Suportados"; color: textMuted; font.pixelSize: 9 }
                                            Text {
                                                text: "7 Provedores (OpenAI, Anthropic, Gemini, Groq, OpenRouter, LM Studio, Ollama)"
                                                color: textPrimary
                                                font.pixelSize: 11
                                                font.weight: Font.DemiBold
                                            }
                                        }
                                    }

                                    Item { Layout.fillWidth: true }

                                    JarvisButton {
                                        variant: "secondary"
                                        text: "↻  Atualizar"
                                        implicitHeight: 32
                                        leftPadding: 12; rightPadding: 12
                                        textSize: 8
                                        onClicked: jarvisBackend.aiAgentsChanged()
                                    }
                                }
                            }

                            // Lista / Cards de Modelos de IA
                            ScrollView {
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                contentWidth: availableWidth
                                clip: true

                                ColumnLayout {
                                    width: parent.width
                                    spacing: 16

                                    // Empty State se não houver modelos configurados
                                    Rectangle {
                                        visible: !jarvisBackend.aiAgents || jarvisBackend.aiAgents.length === 0
                                        Layout.fillWidth: true
                                        implicitHeight: 220
                                        radius: 14
                                        color: window.isDark ? "#0A172B" : "#F8FAFC"
                                        border.color: window.isDark ? "#183650" : "#CBD5E1"

                                        ColumnLayout {
                                            anchors.centerIn: parent
                                            spacing: 12

                                            Rectangle {
                                                width: 52; height: 52; radius: 26
                                                color: window.isDark ? "#123049" : "#E0F2FE"
                                                Layout.alignment: Qt.AlignHCenter
                                                Text { anchors.centerIn: parent; text: "🤖"; font.pixelSize: 24 }
                                            }

                                            Text {
                                                text: "Nenhum Modelo de IA configurado no momento"
                                                color: textPrimary
                                                font.pixelSize: 13
                                                font.weight: Font.DemiBold
                                                Layout.alignment: Qt.AlignHCenter
                                            }

                                            Text {
                                                text: "Clique no botão abaixo para definir o provedor (OpenAI, Anthropic, Gemini, Groq, etc.), selecionar o modelo e testar a conexão."
                                                color: textMuted
                                                font.pixelSize: 10
                                                Layout.alignment: Qt.AlignHCenter
                                            }

                                            JarvisButton {
                                                variant: "success"
                                                text: "+  Configurar Primeiro Modelo"
                                                Layout.alignment: Qt.AlignHCenter
                                                implicitHeight: 36
                                                onClicked: agentEditorModal.openNew()
                                            }
                                        }
                                    }

                                    // Grid de Cards dos Modelos
                                    Flow {
                                        Layout.fillWidth: true
                                        spacing: 16
                                        visible: jarvisBackend.aiAgents && jarvisBackend.aiAgents.length > 0

                                        Repeater {
                                            model: jarvisBackend.aiAgents || []
                                            delegate: Rectangle {
                                                width: 380
                                                implicitHeight: agentCardCol.implicitHeight + 36
                                                radius: 14
                                                color: window.isDark ? "#0A172B" : "#FFFFFF"
                                                border.color: modelData.active ? (window.isDark ? "#18503C" : "#86EFAC") : (window.isDark ? "#1B3048" : "#CBD5E1")
                                                border.width: 1.5

                                                ColumnLayout {
                                                    id: agentCardCol
                                                    anchors.fill: parent
                                                    anchors.margins: 18
                                                    spacing: 12

                                                    // Header do Card
                                                    RowLayout {
                                                        Layout.fillWidth: true
                                                        spacing: 12

                                                        Rectangle {
                                                            width: 40; height: 40; radius: 20
                                                            color: window.isDark ? "#123049" : "#E0F2FE"
                                                            border.color: cyan
                                                            Text { anchors.centerIn: parent; text: "🤖"; font.pixelSize: 18 }
                                                        }

                                                        Column {
                                                            Layout.fillWidth: true
                                                            spacing: 2
                                                            Text {
                                                                text: modelData.name || ("Modelo " + (modelData.provider || "IA"))
                                                                color: textPrimary
                                                                font.pixelSize: 13
                                                                font.weight: Font.DemiBold
                                                                elide: Text.ElideRight
                                                            }
                                                            Text {
                                                                text: (modelData.provider || "OpenAI") + " // " + (modelData.model || "gpt-4o")
                                                                color: cyan
                                                                font.pixelSize: 9
                                                                font.weight: Font.Medium
                                                            }
                                                        }

                                                        Rectangle {
                                                            implicitHeight: 22
                                                            implicitWidth: 64
                                                            radius: 11
                                                            color: modelData.active ? (window.isDark ? "#0E2822" : "#E6F4EA") : (window.isDark ? "#2A1820" : "#FEE2E2")
                                                            border.color: modelData.active ? (window.isDark ? "#1E824C" : "#A8DAB5") : "#EF4444"
                                                            Text {
                                                                anchors.centerIn: parent
                                                                text: modelData.active ? "● ATIVO" : "○ INATIVO"
                                                                font.pixelSize: 8
                                                                font.weight: Font.Bold
                                                                color: modelData.active ? green : "#EF4444"
                                                            }
                                                        }
                                                    }

                                                    // Detalhes (Base URL e API Key)
                                                    RowLayout {
                                                        Layout.fillWidth: true
                                                        spacing: 12
                                                        Text {
                                                            text: modelData.base_url ? ("🌐 " + modelData.base_url) : "🌐 Endpoint Oficial"
                                                            color: textMuted
                                                            font.pixelSize: 9
                                                            elide: Text.ElideRight
                                                            Layout.fillWidth: true
                                                        }
                                                        Text {
                                                            text: modelData.api_key ? "🔑 Chave Configurada" : ((modelData.provider === "LM Studio" || modelData.provider === "Ollama") ? "💻 Local (sem chave)" : "⚠️ Sem chave")
                                                            color: modelData.api_key || (modelData.provider === "LM Studio" || modelData.provider === "Ollama") ? green : "#F6C453"
                                                            font.pixelSize: 9
                                                            font.weight: Font.Medium
                                                        }
                                                    }

                                                    Rectangle { Layout.fillWidth: true; height: 1; color: window.isDark ? "#152A42" : "#E2E8F0" }

                                                    // Ações
                                                    RowLayout {
                                                        Layout.fillWidth: true
                                                        spacing: 8

                                                        JarvisButton {
                                                            variant: "secondary"
                                                            text: "⚡  Testar"
                                                            implicitHeight: 32
                                                            leftPadding: 10; rightPadding: 10
                                                            textSize: 8
                                                            onClicked: jarvisBackend.testAiModelConnection(modelData.provider, modelData.model, modelData.api_key, modelData.base_url)
                                                        }

                                                        Item { Layout.fillWidth: true }

                                                        JarvisButton {
                                                            variant: "secondary"
                                                            text: "✎  Editar"
                                                            implicitHeight: 32
                                                            leftPadding: 10; rightPadding: 10
                                                            textSize: 8
                                                            onClicked: agentEditorModal.openEdit(modelData)
                                                        }

                                                        JarvisButton {
                                                            variant: "danger"
                                                            text: "🗑"
                                                            width: 32; height: 32
                                                            textSize: 11
                                                            ToolTip.visible: hovered
                                                            ToolTip.text: "Remover agente"
                                                            ToolTip.delay: 300
                                                            onClicked: jarvisBackend.deleteAiAgent(modelData.id)
                                                        }
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }

                        // ======================================================== ABA 1: COMUNICAÇÃO (AGENTES DE ATENDIMENTO)
                        ColumnLayout {
                            visible: comunicacaoPanel.commMainTab === 1
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            spacing: 16

                            // Cabeçalho da Aba Comunicação
                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 16

                                Column {
                                    Layout.fillWidth: true
                                    spacing: 4

                                    Text {
                                        text: "CANAL DE ATENDIMENTO & COMUNICAÇÃO"
                                        color: cyan
                                        font.pixelSize: 10
                                        font.weight: Font.DemiBold
                                        font.letterSpacing: 1.5
                                    }
                                    Text {
                                        text: "Agentes de Atendimento Inteligente"
                                        color: textPrimary
                                        font.pixelSize: 18
                                        font.weight: Font.DemiBold
                                        font.letterSpacing: 1.1
                                    }
                                    Text {
                                        text: "Crie agentes de IA personalizados com perfil, personalidade, função e base de conhecimento da empresa para atendimento WhatsApp."
                                        color: textMuted
                                        font.pixelSize: 10
                                    }
                                }

                                Item { Layout.fillWidth: true }

                                JarvisButton {
                                    variant: "success"
                                    text: "+  Criar Agente de IA"
                                    implicitHeight: 38
                                    leftPadding: 16; rightPadding: 16
                                    onClicked: communicationAgentModal.openNew()
                                }
                            }

                            // Barra de Métricas
                            Rectangle {
                                Layout.fillWidth: true
                                Layout.preferredHeight: 64
                                radius: 12
                                color: window.isDark ? "#0A1526" : "#F8FAFC"
                                border.color: window.isDark ? "#183650" : "#CBD5E1"

                                RowLayout {
                                    anchors.fill: parent
                                    anchors.leftMargin: 20
                                    anchors.rightMargin: 20
                                    spacing: 20

                                    // Métrica 1: Agentes de Atendimento
                                    Row {
                                        spacing: 12
                                        Rectangle {
                                            width: 36; height: 36; radius: 18
                                            color: window.isDark ? "#0E2822" : "#DCFCE7"
                                            anchors.verticalCenter: parent.verticalCenter
                                            Text { anchors.centerIn: parent; text: "🤖"; font.pixelSize: 15 }
                                        }
                                        Column {
                                            anchors.verticalCenter: parent.verticalCenter
                                            spacing: 2
                                            Text { text: "Agentes de Atendimento"; color: textMuted; font.pixelSize: 9 }
                                            Text {
                                                text: "" + (jarvisBackend.communicationAgents ? jarvisBackend.communicationAgents.length : 0)
                                                color: textPrimary
                                                font.pixelSize: 14
                                                font.weight: Font.Bold
                                            }
                                        }
                                    }

                                    Rectangle { width: 1; height: 30; color: window.isDark ? "#1C3650" : "#E2E8F0" }

                                    // Métrica 2: Modelos de IA Disponíveis
                                    Row {
                                        spacing: 12
                                        Rectangle {
                                            width: 36; height: 36; radius: 18
                                            color: window.isDark ? "#123049" : "#E0F2FE"
                                            anchors.verticalCenter: parent.verticalCenter
                                            Text { anchors.centerIn: parent; text: "⚡"; font.pixelSize: 15 }
                                        }
                                        Column {
                                            anchors.verticalCenter: parent.verticalCenter
                                            spacing: 2
                                            Text { text: "Modelos de IA Salvos"; color: textMuted; font.pixelSize: 9 }
                                            Text {
                                                text: "" + (jarvisBackend.aiAgents ? jarvisBackend.aiAgents.length : 0) + " Modelos configurados"
                                                color: textPrimary
                                                font.pixelSize: 11
                                                font.weight: Font.DemiBold
                                            }
                                        }
                                    }

                                    Rectangle { width: 1; height: 30; color: window.isDark ? "#1C3650" : "#E2E8F0" }

                                    // Métrica 3: WhatsApp
                                    Row {
                                        spacing: 12
                                        Rectangle {
                                            width: 36; height: 36; radius: 18
                                            color: jarvisBackend.whatsappConnected ? (window.isDark ? "#0E2822" : "#DCFCE7") : (window.isDark ? "#2A1820" : "#FEE2E2")
                                            anchors.verticalCenter: parent.verticalCenter
                                            Text { anchors.centerIn: parent; text: "💬"; font.pixelSize: 15 }
                                        }
                                        Column {
                                            anchors.verticalCenter: parent.verticalCenter
                                            spacing: 2
                                            Text { text: "Canal WhatsApp"; color: textMuted; font.pixelSize: 9 }
                                            Text {
                                                text: jarvisBackend.whatsappConnected ? "● Online / Conectado" : "○ Desconectado"
                                                color: jarvisBackend.whatsappConnected ? green : "#EF4444"
                                                font.pixelSize: 11
                                                font.weight: Font.DemiBold
                                            }
                                        }
                                    }

                                    Item { Layout.fillWidth: true }

                                    JarvisButton {
                                        variant: "secondary"
                                        text: "↻  Atualizar"
                                        implicitHeight: 32
                                        leftPadding: 12; rightPadding: 12
                                        textSize: 8
                                        onClicked: jarvisBackend.communicationAgentsChanged()
                                    }
                                }
                            }

                            // Lista / Cards de Agentes de Atendimento
                            ScrollView {
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                contentWidth: availableWidth
                                clip: true

                                ColumnLayout {
                                    width: parent.width
                                    spacing: 16

                                    // Empty State
                                    Rectangle {
                                        visible: !jarvisBackend.communicationAgents || jarvisBackend.communicationAgents.length === 0
                                        Layout.fillWidth: true
                                        implicitHeight: 220
                                        radius: 14
                                        color: window.isDark ? "#0A172B" : "#F8FAFC"
                                        border.color: window.isDark ? "#183650" : "#CBD5E1"

                                        ColumnLayout {
                                            anchors.centerIn: parent
                                            spacing: 12

                                            Rectangle {
                                                width: 52; height: 52; radius: 26
                                                color: window.isDark ? "#0E2822" : "#DCFCE7"
                                                Layout.alignment: Qt.AlignHCenter
                                                Text { anchors.centerIn: parent; text: "🤖"; font.pixelSize: 24 }
                                            }

                                            Text {
                                                text: "Nenhum Agente de IA cadastrado para atendimento"
                                                color: textPrimary
                                                font.pixelSize: 13
                                                font.weight: Font.DemiBold
                                                Layout.alignment: Qt.AlignHCenter
                                            }

                                            Text {
                                                text: "Clique no botão abaixo para definir o perfil (nome, cargo), personalidade (tom, emojis), função e selecionar a IA configurada."
                                                color: textMuted
                                                font.pixelSize: 10
                                                Layout.alignment: Qt.AlignHCenter
                                            }

                                            JarvisButton {
                                                variant: "success"
                                                text: "+  Criar Primeiro Agente de IA"
                                                Layout.alignment: Qt.AlignHCenter
                                                implicitHeight: 36
                                                onClicked: communicationAgentModal.openNew()
                                            }
                                        }
                                    }

                                    // Grid de Cards dos Agentes
                                    Flow {
                                        Layout.fillWidth: true
                                        spacing: 16
                                        visible: jarvisBackend.communicationAgents && jarvisBackend.communicationAgents.length > 0

                                        Repeater {
                                            model: jarvisBackend.communicationAgents || []
                                            delegate: Rectangle {
                                                width: 400
                                                implicitHeight: commCardCol.implicitHeight + 36
                                                radius: 14
                                                color: window.isDark ? "#0A172B" : "#FFFFFF"
                                                border.color: modelData.active ? (window.isDark ? "#18503C" : "#86EFAC") : (window.isDark ? "#1B3048" : "#CBD5E1")
                                                border.width: 1.5

                                                ColumnLayout {
                                                    id: commCardCol
                                                    anchors.fill: parent
                                                    anchors.margins: 18
                                                    spacing: 12

                                                    // Header do Card
                                                    RowLayout {
                                                        Layout.fillWidth: true
                                                        spacing: 12

                                                        Rectangle {
                                                            width: 42; height: 42; radius: 21
                                                            color: window.isDark ? "#0E2822" : "#DCFCE7"
                                                            border.color: green
                                                            Text { anchors.centerIn: parent; text: "🤖"; font.pixelSize: 20 }
                                                        }

                                                        Column {
                                                            Layout.fillWidth: true
                                                            spacing: 2
                                                            Text {
                                                                text: modelData.name || "Agente sem nome"
                                                                color: textPrimary
                                                                font.pixelSize: 14
                                                                font.weight: Font.DemiBold
                                                                elide: Text.ElideRight
                                                            }
                                                            Text {
                                                                text: (modelData.role || "Atendente") + (modelData.gender ? " • " + modelData.gender : "") + (modelData.age ? " (" + modelData.age + " anos)" : "")
                                                                color: green
                                                                font.pixelSize: 9
                                                                font.weight: Font.Medium
                                                            }
                                                        }

                                                        Rectangle {
                                                            implicitHeight: 22
                                                            implicitWidth: 64
                                                            radius: 11
                                                            color: modelData.active ? (window.isDark ? "#0E2822" : "#E6F4EA") : (window.isDark ? "#2A1820" : "#FEE2E2")
                                                            border.color: modelData.active ? (window.isDark ? "#1E824C" : "#A8DAB5") : "#EF4444"
                                                            Text {
                                                                anchors.centerIn: parent
                                                                text: modelData.active ? "● ATIVO" : "○ INATIVO"
                                                                font.pixelSize: 8
                                                                font.weight: Font.Bold
                                                                color: modelData.active ? green : "#EF4444"
                                                            }
                                                        }
                                                    }

                                                    // Modelo de IA Vinculado
                                                    Rectangle {
                                                        Layout.fillWidth: true
                                                        implicitHeight: 32
                                                        radius: 8
                                                        color: window.isDark ? "#0D1E30" : "#F0F9FF"
                                                        border.color: window.isDark ? "#1E3D5F" : "#BAE6FD"

                                                        RowLayout {
                                                            anchors.fill: parent
                                                            anchors.leftMargin: 10
                                                            anchors.rightMargin: 10
                                                            spacing: 8
                                                            Text { text: "🧠"; font.pixelSize: 12 }
                                                            Text {
                                                                text: "IA: " + (modelData.model_name ? modelData.model_name : "Nenhum modelo vinculado")
                                                                color: cyan
                                                                font.pixelSize: 9
                                                                font.weight: Font.DemiBold
                                                                Layout.fillWidth: true
                                                                elide: Text.ElideRight
                                                            }
                                                        }
                                                    }

                                                    // Box de Personalidade & Função
                                                    Rectangle {
                                                        Layout.fillWidth: true
                                                        implicitHeight: 52
                                                        radius: 8
                                                        color: window.isDark ? "#060D19" : "#F8FAFC"
                                                        border.color: window.isDark ? "#14283E" : "#E2E8F0"

                                                        Column {
                                                            anchors.fill: parent
                                                            anchors.margins: 8
                                                            spacing: 3
                                                            Text {
                                                                text: "Tom: " + (modelData.tone || "Amigável") + " • Formalidade: " + (modelData.formality || "Equilibrado") + " • Emojis: " + (modelData.emoji_level || "Normal")
                                                                color: textPrimary
                                                                font.pixelSize: 9
                                                                font.weight: Font.Medium
                                                            }
                                                            Text {
                                                                text: modelData.job_description ? modelData.job_description : "Sem descrição de função definida."
                                                                color: textMuted
                                                                font.pixelSize: 9
                                                                elide: Text.ElideRight
                                                                maximumLineCount: 1
                                                            }
                                                        }
                                                    }

                                                    // Empresa vinculada
                                                    Text {
                                                        visible: modelData.company_name !== ""
                                                        text: "🏢 " + modelData.company_name + (modelData.company_segment ? " (" + modelData.company_segment + ")" : "")
                                                        color: textMuted
                                                        font.pixelSize: 9
                                                        elide: Text.ElideRight
                                                        Layout.fillWidth: true
                                                    }

                                                    Rectangle { Layout.fillWidth: true; height: 1; color: window.isDark ? "#152A42" : "#E2E8F0" }

                                                    // Ações
                                                    RowLayout {
                                                        Layout.fillWidth: true
                                                        spacing: 8

                                                        Item { Layout.fillWidth: true }

                                                        JarvisButton {
                                                            variant: "secondary"
                                                            text: "✎  Editar"
                                                            implicitHeight: 32
                                                            leftPadding: 12; rightPadding: 12
                                                            textSize: 8
                                                            onClicked: communicationAgentModal.openEdit(modelData)
                                                        }

                                                        JarvisButton {
                                                            variant: "danger"
                                                            text: "🗑"
                                                            width: 32; height: 32
                                                            textSize: 11
                                                            ToolTip.visible: hovered
                                                            ToolTip.text: "Remover agente de atendimento"
                                                            ToolTip.delay: 300
                                                            onClicked: jarvisBackend.deleteCommunicationAgent(modelData.id)
                                                        }
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }

                // ============================================ SETOR SAÚDE: PACIENTES
                Rectangle {
                    id: patientsPanel
                    objectName: "patientsPanel"
                    anchors.fill: parent
                    anchors.margins: 20
                    visible: jarvisBackend.currentView === "pacientes"
                    radius: 16
                    color: window.isDark ? "#070E1E" : "#FFFFFF"
                    border.color: window.isDark ? "#152A44" : "#CBD5E1"

                    property var rows: []
                    function reload() { rows = jarvisBackend.searchPatients(patFilter.text) }

                    Connections {
                        target: jarvisBackend
                        function onPatientsChanged() { if (patientsPanel.visible) patientsPanel.reload() }
                    }
                    onVisibleChanged: if (visible) reload()
                    Component.onCompleted: reload()

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 24
                        spacing: 14

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 12
                            Text { text: "PACIENTES"; color: textPrimary; font.pixelSize: 18; font.weight: Font.DemiBold; font.letterSpacing: 2 }
                            Item { Layout.fillWidth: true }
                            TextField {
                                id: patFilter
                                Layout.preferredWidth: 300; Layout.preferredHeight: 38
                                placeholderText: "🔎  buscar por nome, documento, telefone"
                                placeholderTextColor: window.isDark ? "#526D83" : "#94A3B8"
                                color: textPrimary; font.pixelSize: 11; leftPadding: 12
                                background: Rectangle { radius: 9; color: inputBg; border.color: parent.activeFocus ? cyan : inputBorder }
                                onTextChanged: patientsPanel.reload()
                            }
                            JarvisButton {
                                variant: "success"; text: "＋  CADASTRAR PACIENTE"; implicitHeight: 38; textSize: 10
                                onClicked: patientModal.openNew()
                            }
                        }

                        Text {
                            Layout.fillWidth: true
                            visible: patientsPanel.rows.length === 0
                            text: patFilter.text ? "Nenhum paciente encontrado para \"" + patFilter.text + "\"."
                                                 : "Nenhum paciente cadastrado. Clique em ＋ CADASTRAR PACIENTE."
                            color: textMuted; font.pixelSize: 11
                        }

                        GridView {
                            id: patGrid
                            Layout.fillWidth: true; Layout.fillHeight: true
                            clip: true
                            cellWidth: Math.floor(width / Math.max(1, Math.floor(width / 300)))
                            cellHeight: 128
                            model: patientsPanel.rows
                            delegate: Item {
                                width: patGrid.cellWidth; height: patGrid.cellHeight
                                Rectangle {
                                    anchors.fill: parent
                                    anchors.margins: 6
                                    radius: 12
                                    color: pcMouse.containsMouse ? (window.isDark ? "#0E2036" : "#EFF6FF") : (window.isDark ? "#0A172B" : "#F8FAFC")
                                    border.color: pcMouse.containsMouse ? cyan : (window.isDark ? "#1F3B57" : "#E2E8F0")
                                    Column {
                                        anchors.fill: parent
                                        anchors.margins: 13
                                        spacing: 5
                                        Text { text: modelData.name; color: textPrimary; font.pixelSize: 13; font.weight: Font.DemiBold; elide: Text.ElideRight; width: parent.width }
                                        Text {
                                            text: [modelData.ageLabel, ({M:"Masculino",F:"Feminino",O:"Outro"})[modelData.sex] || "", modelData.document].filter(function(x){return x}).join("  ·  ")
                                            color: textMuted; font.pixelSize: 9; elide: Text.ElideRight; width: parent.width
                                        }
                                        Row {
                                            spacing: 6
                                            Rectangle {
                                                visible: (modelData.allergies || "") !== ""
                                                radius: 5; color: window.isDark ? "#3A1622" : "#FEE2E2"
                                                height: 18; width: alergiaT.width + 14
                                                Text { id: alergiaT; anchors.centerIn: parent; text: "⚠ alergias"; color: danger; font.pixelSize: 8; font.weight: Font.DemiBold }
                                            }
                                            Rectangle {
                                                visible: (modelData.conditions || "") !== ""
                                                radius: 5; color: window.isDark ? "#1F1633" : "#F3E8FF"
                                                height: 18; width: condT.width + 14
                                                Text { id: condT; anchors.centerIn: parent; text: "condições"; color: violet; font.pixelSize: 8; font.weight: Font.DemiBold }
                                            }
                                        }
                                        Text {
                                            width: parent.width
                                            text: (modelData.conditions || modelData.medications || modelData.notes || "").slice(0, 70)
                                            color: textMuted; font.pixelSize: 8; elide: Text.ElideRight; maximumLineCount: 2; wrapMode: Text.Wrap
                                        }
                                    }
                                    MouseArea {
                                        id: pcMouse
                                        anchors.fill: parent
                                        hoverEnabled: true
                                        cursorShape: Qt.PointingHandCursor
                                        onClicked: patientModal.openEdit(modelData.id)
                                    }
                                }
                            }
                        }
                    }
                }

                // ============================================ SETOR SAÚDE: EXAMES & DOCS
                Rectangle {
                    id: laudosPanel
                    objectName: "laudosPanel"
                    anchors.fill: parent
                    anchors.margins: 20
                    visible: jarvisBackend.currentView === "laudos"
                    radius: 16
                    color: window.isDark ? "#070E1E" : "#FFFFFF"
                    border.color: window.isDark ? "#152A44" : "#CBD5E1"

                    property var patientList: []
                    property var records: []
                    property int patientId: -1
                    readonly property var kindOptions: ["Todos", "Laudo", "Exame / resultado", "Consulta", "Evolução", "Prescrição", "Nota"]
                    readonly property var kindIds: ["", "laudo", "exame", "consulta", "evolucao", "prescricao", "nota"]

                    function reloadPatients() {
                        patientList = jarvisBackend.patients
                        var target = window.activePatientId > 0 ? window.activePatientId
                                   : (patientId > 0 ? patientId
                                   : (patientList.length ? patientList[0].id : -1))
                        setPatient(target)
                    }
                    function setPatient(id) {
                        patientId = id
                        for (var i = 0; i < patientList.length; i++)
                            if (patientList[i].id === id) ldPatientPicker.currentIndex = i
                        reloadRecords()
                    }
                    function reloadRecords() {
                        var all = patientId > 0 ? jarvisBackend.patientRecords(patientId) : []
                        var kf = kindIds[ldKindFilter.currentIndex]
                        records = kf ? all.filter(function(r){ return r.kind === kf }) : all
                    }
                    Connections {
                        target: jarvisBackend
                        function onPatientRecordsChanged() { if (laudosPanel.visible) laudosPanel.reloadRecords() }
                        function onPatientsChanged() { if (laudosPanel.visible) laudosPanel.reloadPatients() }
                    }
                    onVisibleChanged: if (visible) reloadPatients()
                    Component.onCompleted: reloadPatients()

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 24
                        spacing: 14

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: "EXAMES & DOCS"; color: textPrimary; font.pixelSize: 18; font.weight: Font.DemiBold; font.letterSpacing: 2 }
                            Item { Layout.fillWidth: true }
                            FuturisticCombo {
                                id: ldPatientPicker
                                Layout.preferredWidth: 240; Layout.preferredHeight: 36
                                model: laudosPanel.patientList.map(function(p){ return p.name + (p.ageLabel ? "  (" + p.ageLabel + ")" : "") })
                                onActivated: if (laudosPanel.patientList[currentIndex]) laudosPanel.setPatient(laudosPanel.patientList[currentIndex].id)
                            }
                            FuturisticCombo {
                                id: ldKindFilter
                                Layout.preferredWidth: 150; Layout.preferredHeight: 36
                                model: laudosPanel.kindOptions
                                onActivated: laudosPanel.reloadRecords()
                            }
                            JarvisButton {
                                variant: "success"; text: "＋  NOVO REGISTRO"; implicitHeight: 36; textSize: 9
                                enabled: laudosPanel.patientId > 0
                                onClicked: recordModal.openNew(laudosPanel.patientId)
                            }
                        }

                        Text {
                            Layout.fillWidth: true
                            visible: laudosPanel.patientId <= 0
                            text: "Cadastre um paciente em PACIENTES para abrir o prontuário."
                            color: textMuted; font.pixelSize: 11
                        }
                        Text {
                            Layout.fillWidth: true
                            visible: laudosPanel.patientId > 0 && laudosPanel.records.length === 0
                            text: "Nenhum registro para este paciente. Clique em ＋ NOVO REGISTRO para adicionar um laudo, exame ou evolução."
                            color: textMuted; font.pixelSize: 11
                        }

                        GridView {
                            id: ldGrid
                            Layout.fillWidth: true; Layout.fillHeight: true
                            clip: true
                            cellWidth: Math.floor(width / Math.max(1, Math.floor(width / 320)))
                            cellHeight: 140
                            model: laudosPanel.records
                            delegate: Item {
                                width: ldGrid.cellWidth; height: ldGrid.cellHeight
                                Rectangle {
                                    anchors.fill: parent
                                    anchors.margins: 6
                                    radius: 12
                                    color: rcMouse.containsMouse ? (window.isDark ? "#0E2036" : "#EFF6FF") : (window.isDark ? "#0A172B" : "#F8FAFC")
                                    border.color: {
                                        var risk = modelData.risk || ""
                                        if (risk === "critico" || risk === "alto") return danger
                                        if (risk === "moderado") return amber
                                        return rcMouse.containsMouse ? cyan : (window.isDark ? "#1F3B57" : "#E2E8F0")
                                    }
                                    Column {
                                        anchors.fill: parent
                                        anchors.margins: 13
                                        spacing: 4
                                        Row {
                                            spacing: 6
                                            Text { text: modelData.kindLabel; color: cyan; font.pixelSize: 8; font.weight: Font.Bold }
                                            Text { text: modelData.occurred_at || ""; color: textMuted; font.pixelSize: 8 }
                                        }
                                        Text { text: modelData.title || "(sem título)"; color: textPrimary; font.pixelSize: 12; font.weight: Font.DemiBold; elide: Text.ElideRight; width: parent.width }
                                        Text {
                                            width: parent.width
                                            text: (modelData.body || "").slice(0, 90)
                                            color: textMuted; font.pixelSize: 8; wrapMode: Text.Wrap; maximumLineCount: 2; elide: Text.ElideRight
                                        }
                                        Row {
                                            spacing: 8
                                            Text { visible: modelData.fileCount > 0; text: "📎 " + modelData.fileCount; color: textMuted; font.pixelSize: 8 }
                                            Text {
                                                visible: modelData.analyzed
                                                text: {
                                                    var r = modelData.risk || ""
                                                    if (r === "critico") return "⛔ risco crítico"
                                                    if (r === "alto") return "🔴 risco alto"
                                                    if (r === "moderado") return "🟠 risco moderado"
                                                    if (r === "baixo") return "🟢 analisado"
                                                    return "✓ analisado"
                                                }
                                                color: {
                                                    var r = modelData.risk || ""
                                                    if (r === "critico" || r === "alto") return danger
                                                    if (r === "moderado") return amber
                                                    return green
                                                }
                                                font.pixelSize: 8; font.weight: Font.DemiBold
                                            }
                                        }
                                    }
                                    MouseArea {
                                        id: rcMouse
                                        anchors.fill: parent
                                        hoverEnabled: true
                                        cursorShape: Qt.PointingHandCursor
                                        onClicked: recordModal.openEdit(modelData.id, laudosPanel.patientId)
                                    }
                                }
                            }
                        }
                    }
                }

                // overlay para telas ainda não implementadas
                Rectangle {
                    anchors.fill: parent
                    anchors.margins: 20
                    visible: ["hub", "automacao", "agenda", "arquivos", "analises", "sistema", "comunicacao", "pacientes", "laudos"].indexOf(jarvisBackend.currentView) === -1
                    radius: 16
                    color: window.isDark ? "#060C1B" : "#FFFFFF"
                    border.color: window.isDark ? "#152A44" : "#CBD5E1"
                    Column {
                        anchors.centerIn: parent
                        spacing: 10
                        Text {
                            anchors.horizontalCenter: parent.horizontalCenter
                            text: jarvisBackend.currentView.toUpperCase()
                            color: cyan
                            font.pixelSize: 20
                            font.weight: Font.DemiBold
                            font.letterSpacing: 3
                        }
                        Text {
                            anchors.horizontalCenter: parent.horizontalCenter
                            text: "Módulo em construção. Use o HUB, a Automação e o chat por enquanto."
                            color: textMuted
                            font.pixelSize: 11
                        }
                        JarvisButton {
                            anchors.horizontalCenter: parent.horizontalCenter
                            text: "◀  VOLTAR AO HUB"
                            onClicked: jarvisBackend.setView("hub")
                        }
                    }
                }
            }

            // -------------------------------------------------- chat
            Rectangle {
                Layout.preferredWidth: 432
                Layout.minimumWidth: 432
                Layout.fillHeight: true
                color: window.isDark ? "#070D1D" : "#FFFFFF"
                border.color: window.isDark ? "#12243C" : "#CBD5E1"
                border.width: 1

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 16
                    spacing: 12

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 4
                        Text {
                            text: "JARVIS CHAT"
                            color: textPrimary
                            font.pixelSize: 13
                            font.weight: Font.DemiBold
                            font.letterSpacing: 1.8
                        }
                        Item { Layout.fillWidth: true }

                        JarvisButton {
                            variant: "icon"
                            Layout.preferredWidth: 32
                            Layout.preferredHeight: 30
                            Layout.alignment: Qt.AlignVCenter
                            text: "+"
                            enabled: !jarvisBackend.busy
                            textSize: 15
                            onClicked: jarvisBackend.newConversation()
                            ToolTip.visible: hovered
                            ToolTip.text: "Nova conversa"
                            ToolTip.delay: 400
                        }
                        JarvisButton {
                            variant: "secondary"
                            customRadius: 8
                            Layout.preferredWidth: 32
                            Layout.preferredHeight: 30
                            Layout.alignment: Qt.AlignVCenter
                            leftPadding: 0; rightPadding: 0
                            text: "🕘"
                            textSize: 12
                            onClicked: historyDialog.open()
                            ToolTip.visible: hovered
                            ToolTip.text: "Histórico de conversas"
                            ToolTip.delay: 400
                        }
                        JarvisButton {
                            variant: "secondary"
                            customRadius: 8
                            Layout.preferredWidth: 32
                            Layout.preferredHeight: 30
                            Layout.alignment: Qt.AlignVCenter
                            leftPadding: 0; rightPadding: 0
                            text: "🧠"
                            textSize: 13
                            onClicked: memoryManagerModal.open()
                            ToolTip.visible: hovered
                            ToolTip.text: "Memória Contextual & Aprendizado"
                            ToolTip.delay: 400
                        }
                        JarvisButton {
                            variant: "secondary"
                            customRadius: 8
                            Layout.preferredWidth: 32
                            Layout.preferredHeight: 30
                            Layout.alignment: Qt.AlignVCenter
                            leftPadding: 0; rightPadding: 0
                            text: "⚙"
                            textSize: 13
                            onClicked: { settingsDialog.tab = 0; settingsDialog.open() }
                            ToolTip.visible: hovered
                            ToolTip.text: "Configurações"
                            ToolTip.delay: 400
                        }
                    }

                    FuturisticCombo {
                        id: providerBox
                        Layout.fillWidth: true
                        Layout.preferredHeight: 38
                        model: jarvisBackend.providers
                    }

                    // ----- perfil de uso
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 5

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 6
                            Repeater {
                                model: jarvisBackend.usageProfiles
                                delegate: Rectangle {
                                    readonly property bool hiddenBySector:
                                        (jarvisBackend.hiddenProfiles || []).indexOf(modelData.id) !== -1
                                    visible: !hiddenBySector
                                    Layout.fillWidth: !hiddenBySector
                                    Layout.preferredWidth: hiddenBySector ? 0 : -1
                                    Layout.preferredHeight: 34
                                    radius: 9
                                    property bool active: jarvisBackend.usageProfile === modelData.id
                                    color: active ? (window.isDark ? "#123247" : "#E0F2FE")
                                           : (profMouse.containsMouse ? (window.isDark ? "#101f34" : "#F1F5F9") : (window.isDark ? "#0B1729" : "#F8FAFC"))
                                    border.color: active ? cyan : (window.isDark ? "#1F3B57" : "#CBD5E1")
                                    border.width: active ? 2 : 1
                                    Text {
                                        anchors.fill: parent
                                        anchors.margins: 3
                                        text: modelData.icon + " " + modelData.name
                                        color: active ? cyan : textPrimary
                                        font.pixelSize: 9
                                        font.weight: Font.DemiBold
                                        horizontalAlignment: Text.AlignHCenter
                                        verticalAlignment: Text.AlignVCenter
                                        wrapMode: Text.NoWrap
                                        elide: Text.ElideRight
                                    }
                                    MouseArea {
                                        id: profMouse
                                        anchors.fill: parent
                                        hoverEnabled: true
                                        cursorShape: Qt.PointingHandCursor
                                        enabled: !jarvisBackend.busy
                                        onClicked: jarvisBackend.setProfile(modelData.id)
                                    }
                                }
                            }
                        }

                        Text {
                            Layout.fillWidth: true
                            text: jarvisBackend.usageProfileInfo.tagline || ""
                            color: textMuted
                            font.pixelSize: 8
                            font.letterSpacing: 0.5
                            horizontalAlignment: Text.AlignHCenter
                            elide: Text.ElideRight
                        }

                        Text {
                            Layout.fillWidth: true
                            visible: jarvisBackend.devFolder !== ""
                                     && jarvisBackend.usageProfile === "desenvolvimento"
                            text: "📁 " + jarvisBackend.devFolder + "  —  clique para trocar a pasta"
                            color: cyan
                            opacity: 0.8
                            font.pixelSize: 8
                            elide: Text.ElideMiddle
                            MouseArea {
                                anchors.fill: parent
                                cursorShape: Qt.PointingHandCursor
                                onClicked: devFolderDialog.open()
                            }
                        }

                        JarvisButton {
                            Layout.fillWidth: true
                            implicitHeight: 30
                            visible: jarvisBackend.usageProfile === "seguranca"
                            enabled: !jarvisBackend.busy
                            text: "🛡  FERRAMENTAS DE SEGURANÇA"
                            textSize: 9
                            onClicked: securityPanel.open()
                        }

                        JarvisButton {
                            Layout.fillWidth: true
                            implicitHeight: 30
                            visible: jarvisBackend.usageProfile === "desenvolvimento"
                            enabled: !jarvisBackend.busy
                            text: "💻  ASSISTENTE DE CÓDIGO"
                            textSize: 9
                            onClicked: codePanel.open()
                        }

                        JarvisButton {
                            Layout.fillWidth: true
                            implicitHeight: 30
                            visible: jarvisBackend.sector === "saude"
                            enabled: !jarvisBackend.busy
                            text: "🩺  APOIO CLÍNICO"
                            textSize: 9
                            onClicked: healthPanel.open()
                        }
                    }

                    ListView {
                        id: chatView
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        spacing: 14
                        clip: true
                        model: chatModel
                        ScrollBar.vertical: ScrollBar {
                            id: chatScrollBar
                            policy: ScrollBar.AsNeeded
                            width: 6
                            background: Rectangle { color: "transparent" }
                            contentItem: Rectangle {
                                implicitWidth: 6
                                radius: 3
                                color: window.isDark
                                       ? (chatScrollBar.pressed ? cyan : (chatScrollBar.hovered ? "#3B6D94" : "#1B3650"))
                                       : (chatScrollBar.pressed ? "#64748B" : (chatScrollBar.hovered ? "#94A3B8" : "#CBD5E1"))
                            }
                        }

                        delegate: Item {
                            width: chatView.width
                            height: bubble.height + 6

                            Rectangle {
                                id: bubble
                                width: code !== "" ? (parent.width - 20) * 0.96
                                       : image !== "" ? Math.min(parent.width * 0.88, 270)
                                       : Math.min(parent.width * 0.88, Math.max(160, messageText.implicitWidth + 34))
                                height: contentCol.height + 26
                                anchors.right: role === "user" ? parent.right : undefined
                                anchors.left: role === "user" ? undefined : parent.left
                                anchors.rightMargin: role === "user" ? 14 : 0
                                anchors.leftMargin: role === "user" ? 0 : 8
                                radius: 13
                                color: role === "user" ? (window.isDark ? "#14324B" : "#E0F2FE")
                                       : role === "error" ? (window.isDark ? "#351825" : "#FEE2E2")
                                       : (window.isDark ? "#0D1B33" : "#F8FAFC")
                                border.color: role === "user" ? (window.isDark ? "#22627A" : "#BAE6FD")
                                              : role === "error" ? (window.isDark ? "#713044" : "#FCA5A5")
                                              : (window.isDark ? "#1D3856" : "#CBD5E1")

                                HoverHandler { id: bubbleHover }

                                // botao "copiar" no canto (aparece ao passar o mouse)
                                Rectangle {
                                    visible: bubbleHover.hovered && body.length > 0
                                    anchors.top: parent.top
                                    anchors.right: parent.right
                                    anchors.topMargin: 6
                                    anchors.rightMargin: 6
                                    z: 5
                                    width: 52; height: 20; radius: 6
                                    color: copyBubbleMouse.containsMouse
                                           ? (window.isDark ? "#1C4460" : "#BAE6FD")
                                           : (window.isDark ? "#12304A" : "#E0F2FE")
                                    border.color: window.isDark ? "#2C5878" : "#94A3B8"
                                    Text {
                                        anchors.centerIn: parent
                                        text: copyBubbleMouse.done ? "copiado" : "copiar"
                                        color: window.isDark ? "#BFE6F5" : "#0369A1"
                                        font.pixelSize: 8
                                        font.weight: Font.DemiBold
                                    }
                                    MouseArea {
                                        id: copyBubbleMouse
                                        anchors.fill: parent
                                        hoverEnabled: true
                                        cursorShape: Qt.PointingHandCursor
                                        property bool done: false
                                        onClicked: {
                                            jarvisBackend.copyText(body)
                                            done = true
                                            copyResetTimer.restart()
                                        }
                                        Timer { id: copyResetTimer; interval: 1200; onTriggered: copyBubbleMouse.done = false }
                                    }
                                }

                                Column {
                                    id: contentCol
                                    x: 13
                                    y: 13
                                    width: bubble.width - 26
                                    spacing: 7
                                    Text {
                                        text: meta
                                        color: role === "error" ? "#FF8095" : cyan
                                        opacity: 0.78
                                        font.pixelSize: 8
                                        font.weight: Font.DemiBold
                                        font.letterSpacing: 1.1
                                        visible: meta.length > 0
                                    }
                                    TextEdit {
                                        id: messageText
                                        width: parent.width
                                        text: body
                                        color: textPrimary
                                        font.pixelSize: 11
                                        font.family: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
                                        wrapMode: TextEdit.Wrap
                                        readOnly: true
                                        selectByMouse: true
                                        selectionColor: cyan
                                        selectedTextColor: window.isDark ? "#0A1022" : "#FFFFFF"
                                    }

                                    // anexo de imagem embutido na bolha
                                    Rectangle {
                                        visible: image !== ""
                                        width: parent.width
                                        height: Math.max(120, Math.min(220, width * (chatImg.ratio > 0 ? chatImg.ratio : 0.62)))
                                        radius: 8
                                        color: window.isDark ? "#080F1E" : "#FFFFFF"
                                        border.color: window.isDark ? "#1B3958" : "#CBD5E1"
                                        clip: true
                                        Image {
                                            id: chatImg
                                            anchors.fill: parent
                                            anchors.margins: 3
                                            source: image
                                            fillMode: Image.PreserveAspectFit
                                            sourceSize.width: 640
                                            asynchronous: true
                                            readonly property real ratio: (sourceSize.width > 0 && sourceSize.height > 0)
                                                                          ? sourceSize.height / sourceSize.width : 0.62
                                        }
                                        MouseArea {
                                            anchors.fill: parent
                                            cursorShape: Qt.PointingHandCursor
                                            onClicked: if (filePath !== "") jarvisBackend.openFile(filePath)
                                            ToolTip.visible: containsMouse
                                            ToolTip.text: "Abrir a imagem"
                                            hoverEnabled: true
                                        }
                                    }
                                    Rectangle {
                                        visible: fileName !== "" && image === "" && code === ""
                                        width: parent.width
                                        height: visible ? 40 : 0
                                        radius: 8
                                        color: fileMouse.containsMouse
                                               ? (window.isDark ? "#173A50" : "#BAE6FD")
                                               : (window.isDark ? "#10293D" : "#E0F2FE")
                                        border.color: window.isDark ? "#2A4C63" : "#CBD5E1"
                                        Row {
                                            anchors.left: parent.left
                                            anchors.leftMargin: 10
                                            anchors.verticalCenter: parent.verticalCenter
                                            spacing: 8
                                            Text { text: "📄"; font.pixelSize: 14; anchors.verticalCenter: parent.verticalCenter }
                                            Text { text: fileName; color: textPrimary; font.pixelSize: 10; elide: Text.ElideMiddle; width: contentCol.width - 60; anchors.verticalCenter: parent.verticalCenter }
                                        }
                                        MouseArea { id: fileMouse; anchors.fill: parent; hoverEnabled: true; onClicked: if (filePath !== "") jarvisBackend.openFile(filePath) }
                                    }

                                    // ----- cartao de código / artefato gerado pela IA
                                    Rectangle {
                                        id: codeCard
                                        visible: code !== ""
                                        width: parent.width
                                        height: visible ? (codeHead.height + codeBox.height + 22) : 0
                                        radius: 9
                                        color: window.isDark ? "#060B16" : "#FFFFFF"
                                        border.color: window.isDark ? "#1E3B5C" : "#CBD5E1"
                                        clip: true

                                        Column {
                                            x: 9; y: 9
                                            width: parent.width - 18
                                            spacing: 8

                                            RowLayout {
                                                id: codeHead
                                                width: parent.width
                                                spacing: 6

                                                Rectangle {
                                                    radius: 4
                                                    color: window.isDark ? "#122A44" : "#E0F2FE"
                                                    border.color: window.isDark ? "#25507A" : "#BAE6FD"
                                                    Layout.preferredHeight: 18
                                                    Layout.preferredWidth: langLabel.implicitWidth + 14
                                                    Text {
                                                        id: langLabel
                                                        anchors.centerIn: parent
                                                        text: (language || "texto").toUpperCase()
                                                        color: cyan
                                                        font.pixelSize: 8
                                                        font.weight: Font.DemiBold
                                                        font.letterSpacing: 1.0
                                                    }
                                                }
                                                Text {
                                                    text: fileName
                                                    color: textMuted
                                                    font.pixelSize: 9
                                                    elide: Text.ElideMiddle
                                                    Layout.fillWidth: true
                                                }

                                                Repeater {
                                                    model: [
                                                        { "t": "COPIAR", "a": "copy", "show": true },
                                                        { "t": "VISUALIZAR", "a": "view", "show": previewable },
                                                        { "t": "BAIXAR", "a": "down", "show": true }
                                                    ]
                                                    delegate: Rectangle {
                                                        visible: modelData.show
                                                        Layout.preferredHeight: 22
                                                        Layout.preferredWidth: btnLabel.implicitWidth + 18
                                                        radius: 5
                                                        color: btnMouse.containsMouse
                                                               ? (window.isDark ? "#1C4460" : "#BAE6FD")
                                                               : (window.isDark ? "#123047" : "#E0F2FE")
                                                        border.color: window.isDark ? "#2C5878" : "#94A3B8"
                                                        Text {
                                                            id: btnLabel
                                                            anchors.centerIn: parent
                                                            text: modelData.t
                                                            color: window.isDark ? "#BFE6F5" : "#0369A1"
                                                            font.pixelSize: 8
                                                            font.weight: Font.DemiBold
                                                        }
                                                        MouseArea {
                                                            id: btnMouse
                                                            anchors.fill: parent
                                                            hoverEnabled: true
                                                            cursorShape: Qt.PointingHandCursor
                                                            onClicked: {
                                                                if (modelData.a === "copy") {
                                                                    jarvisBackend.copyText(code)
                                                                } else if (modelData.a === "view") {
                                                                    previewDialog.openFor(code, language, fileName)
                                                                } else if (modelData.a === "down") {
                                                                    jarvisBackend.downloadArtifact(fileName, code)
                                                                }
                                                            }
                                                        }
                                                    }
                                                }
                                            }

                                            Rectangle {
                                                id: codeBox
                                                width: parent.width
                                                height: Math.min(codeText.implicitHeight + 14, 220)
                                                radius: 6
                                                color: window.isDark ? "#04070F" : "#F8FAFC"
                                                border.color: window.isDark ? "#14253A" : "#E2E8F0"

                                                ScrollView {
                                                    anchors.fill: parent
                                                    anchors.margins: 7
                                                    clip: true

                                                    TextEdit {
                                                        id: codeText
                                                        width: parent.width
                                                        text: code
                                                        color: textPrimary
                                                        font.family: "Consolas, 'Fira Code', 'Courier New', monospace"
                                                        font.pixelSize: 10
                                                        readOnly: true
                                                        selectByMouse: true
                                                        selectionColor: cyan
                                                        selectedTextColor: window.isDark ? "#0A1022" : "#FFFFFF"
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }

                    Shortcut {
                        sequences: ["Esc"]
                        enabled: speaking
                        onActivated: jarvisBackend.stopSpeaking()
                    }

                    // barra para interromper a fala da IA
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: speaking ? 40 : 0
                        visible: speaking
                        radius: 12
                        color: stopSpeechMouse.containsMouse ? (window.isDark ? "#5A2130" : "#FECACA") : (window.isDark ? "#3A1622" : "#FEE2E2")
                        border.color: "#FF6B8A"
                        border.width: 1
                        clip: true

                        Row {
                            anchors.centerIn: parent
                            spacing: 10
                            Rectangle {
                                width: 14; height: 14; radius: 3
                                color: "#FF8FA6"
                                anchors.verticalCenter: parent.verticalCenter
                            }
                            Text {
                                anchors.verticalCenter: parent.verticalCenter
                                text: "PARAR A RESPOSTA  (ESC)"
                                color: window.isDark ? "#FFC2CE" : "#991B1B"
                                font.pixelSize: 10
                                font.weight: Font.DemiBold
                                font.letterSpacing: 1.4
                            }
                        }
                        MouseArea {
                            id: stopSpeechMouse
                            anchors.fill: parent
                            hoverEnabled: true
                            onClicked: jarvisBackend.stopSpeaking()
                        }
                    }

                    // ----- anexos pendentes (imagens / documentos)
                    Flow {
                        id: attachmentBar
                        Layout.fillWidth: true
                        spacing: 6
                        visible: jarvisBackend.pendingAttachments.length > 0

                        Repeater {
                            model: jarvisBackend.pendingAttachments
                            delegate: Rectangle {
                                height: 26
                                width: chipRow.implicitWidth + 18
                                radius: 13
                                color: modelData.error ? (window.isDark ? "#3A1622" : "#FEE2E2") : (window.isDark ? "#12304A" : "#E0F2FE")
                                border.color: modelData.error ? "#FF6B8A" : (window.isDark ? "#2C5878" : "#94A3B8")

                                Row {
                                    id: chipRow
                                    anchors.centerIn: parent
                                    spacing: 6
                                    Text {
                                        anchors.verticalCenter: parent.verticalCenter
                                        text: modelData.kind === "image" ? "🖼" : "📄"
                                        font.pixelSize: 11
                                    }
                                    Text {
                                        anchors.verticalCenter: parent.verticalCenter
                                        text: modelData.name
                                        color: modelData.error ? (window.isDark ? "#FFC2CE" : "#991B1B") : textPrimary
                                        font.pixelSize: 9
                                        elide: Text.ElideMiddle
                                        maximumLineCount: 1
                                        width: Math.min(implicitWidth, 150)
                                    }
                                    Text {
                                        anchors.verticalCenter: parent.verticalCenter
                                        text: modelData.error ? "erro" : modelData.sizeLabel
                                        color: textMuted
                                        font.pixelSize: 8
                                    }
                                    Rectangle {
                                        width: 15; height: 15; radius: 8
                                        anchors.verticalCenter: parent.verticalCenter
                                        color: closeChip.containsMouse ? "#FF6B8A" : "transparent"
                                        Text {
                                            anchors.centerIn: parent
                                            text: "✕"
                                            color: closeChip.containsMouse ? "white" : textMuted
                                            font.pixelSize: 9
                                        }
                                        MouseArea {
                                            id: closeChip
                                            anchors.fill: parent
                                            hoverEnabled: true
                                            cursorShape: Qt.PointingHandCursor
                                            onClicked: jarvisBackend.removeAttachment(index)
                                        }
                                    }
                                }
                            }
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: Math.max(84, Math.min(inputArea.contentHeight + 40, 176))
                        Behavior on Layout.preferredHeight { NumberAnimation { duration: 90 } }
                        radius: 14
                        color: window.isDark ? "#0A1428" : "#FFFFFF"
                        border.color: listening || speaking ? "#FF6B8A" : inputArea.activeFocus ? cyan : (window.isDark ? "#1B3653" : "#CBD5E1")
                        border.width: 1

                        RowLayout {
                            anchors.fill: parent
                            anchors.margins: 10
                            spacing: 8

                            // ----- anexar arquivo
                            Rectangle {
                                Layout.preferredWidth: 40
                                Layout.preferredHeight: 40
                                radius: 20
                                color: attachMouse.containsMouse
                                       ? (window.isDark ? "#173A50" : "#E0F2FE")
                                       : (window.isDark ? "#10293D" : "#F1F5F9")
                                border.color: jarvisBackend.pendingAttachments.length > 0 ? cyan : (window.isDark ? "#506273" : "#CBD5E1")
                                Text {
                                    anchors.centerIn: parent
                                    text: "📎"
                                    font.pixelSize: 15
                                }
                                MouseArea {
                                    id: attachMouse
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    cursorShape: Qt.PointingHandCursor
                                    enabled: !jarvisBackend.busy && !voiceActive
                                    onClicked: attachmentDialog.open()
                                    ToolTip.visible: containsMouse
                                    ToolTip.text: "Anexar imagem ou documento (PDF, Word, Excel, txt...)"
                                    ToolTip.delay: 300
                                }
                            }

                            Item {
                                width: 44; height: 44

                                Rectangle {
                                    anchors.centerIn: parent
                                    width: 42 + jarvisBackend.voiceLevel * 12
                                    height: width
                                    radius: width / 2
                                    color: "transparent"
                                    border.color: listening ? "#FF6B8A" : cyan
                                    border.width: 1
                                    opacity: listening ? 0.4 + jarvisBackend.voiceLevel * 0.5 : 0
                                    Behavior on width { NumberAnimation { duration: 90 } }
                                }

                                Rectangle {
                                    anchors.centerIn: parent
                                    width: 44; height: 44; radius: 22
                                    color: (listening || speaking) ? (window.isDark ? "#482035" : "#FEE2E2")
                                           : micMouse.containsMouse ? (window.isDark ? "#173A50" : "#E0F2FE")
                                           : (window.isDark ? "#10293D" : "#F1F5F9")
                                    border.color: (listening || speaking) ? "#FF6B8A" : jarvisBackend.voiceAvailable ? cyan : (window.isDark ? "#506273" : "#CBD5E1")
                                    border.width: (listening || speaking) ? 2 : 1

                                    Text {
                                        anchors.centerIn: parent
                                        text: (listening || speaking) ? "\u25A0" : "\u2B24"
                                        color: (listening || speaking) ? "#FF8FA6" : jarvisBackend.voiceAvailable ? cyan : (window.isDark ? "#607586" : "#94A3B8")
                                        font.pixelSize: (listening || speaking) ? 13 : 15
                                    }

                                    SequentialAnimation on scale {
                                        running: listening || speaking
                                        loops: Animation.Infinite
                                        NumberAnimation { to: 1.07; duration: 420; easing.type: Easing.InOutSine }
                                        NumberAnimation { to: 1.0; duration: 420; easing.type: Easing.InOutSine }
                                    }
                                }

                                MouseArea {
                                    id: micMouse
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    onClicked: {
                                        if (speaking)
                                            jarvisBackend.stopSpeaking()
                                        else
                                            jarvisBackend.toggleListening(providerBox.currentText)
                                    }
                                    ToolTip.visible: containsMouse
                                    ToolTip.text: speaking ? "Parar a resposta (Esc)" : jarvisBackend.voiceHint
                                    ToolTip.delay: 250
                                }
                            }

                            ScrollView {
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                clip: true
                                ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
                                ScrollBar.vertical.policy: ScrollBar.AsNeeded
                                TextArea {
                                    id: inputArea
                                    placeholderText: listening ? "Estou ouvindo..." : jarvisBackend.voiceState === "transcribing" ? "Transcrevendo..." : speaking ? ((jarvisBackend.systemName || "Jarvis") + " respondendo...") : jarvisBackend.busy ? "Processando..." : "Digite uma instrução...  (Shift+Enter = nova linha)"
                                    placeholderTextColor: window.isDark ? "#526D83" : "#94A3B8"
                                    color: textPrimary
                                    font.pixelSize: 13
                                    wrapMode: TextEdit.Wrap
                                    enabled: !jarvisBackend.busy && !voiceActive
                                    background: null
                                    selectByMouse: true

                                    // Enter envia; Shift/Ctrl+Enter quebra linha.
                                    // (os sinais especificos de tecla do QML ja marcam
                                    //  accepted=true, entao a quebra e feita na mao.)
                                    function handleReturn(event) {
                                        if (event.modifiers & (Qt.ShiftModifier | Qt.ControlModifier)) {
                                            inputArea.insert(inputArea.cursorPosition, "\n")
                                        } else {
                                            sendButton.clicked()
                                        }
                                        event.accepted = true
                                    }
                                    Keys.onReturnPressed: handleReturn(event)
                                    Keys.onEnterPressed: handleReturn(event)
                                }
                            }

                            Button {
                                id: sendButton
                                width: 48; height: 48
                                enabled: !jarvisBackend.busy && (inputArea.text.trim().length > 0 || jarvisBackend.pendingAttachments.length > 0)
                                background: Rectangle {
                                    radius: 24
                                    gradient: Gradient {
                                        GradientStop { position: 0; color: sendButton.enabled ? cyan : (window.isDark ? "#27404D" : "#CBD5E1") }
                                        GradientStop { position: 1; color: sendButton.enabled ? violet : (window.isDark ? "#1D2D3A" : "#94A3B8") }
                                    }
                                    opacity: sendButton.down ? 0.75 : 1
                                }
                                contentItem: Text {
                                    text: "\u27A4"
                                    color: "white"
                                    horizontalAlignment: Text.AlignHCenter
                                    verticalAlignment: Text.AlignVCenter
                                    font.pixelSize: 17
                                }
                                onClicked: {
                                    var text = inputArea.text.trim()
                                    if (text.length > 0 || jarvisBackend.pendingAttachments.length > 0) {
                                        jarvisBackend.sendMessage(text, providerBox.currentText)
                                        inputArea.clear()
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }

        // -------------------------------------------------------- rodape
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 52
            color: window.isDark ? "#070D1C" : "#FFFFFF"
            border.color: window.isDark ? "#152A42" : "#CBD5E1"
            border.width: 1

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 22
                anchors.rightMargin: 22
                spacing: 26

                Row {
                    spacing: 10
                    Rectangle {
                        width: 24; height: 24; radius: 6
                        color: window.isDark ? "#103449" : "#E0F2FE"
                        anchors.verticalCenter: parent.verticalCenter
                        Text { anchors.centerIn: parent; text: "\u25C9"; color: cyan; font.pixelSize: 12 }
                    }
                    Column {
                        anchors.verticalCenter: parent.verticalCenter
                        Text { text: (jarvisBackend.systemName ? jarvisBackend.systemName.toUpperCase() : "JARVIS") + " OS"; color: textPrimary; font.pixelSize: 10; font.weight: Font.DemiBold }
                        Text {
                            text: "STATUS: " + (stats && stats.available ? "OTIMO" : "INICIANDO")
                            color: green; font.pixelSize: 8; font.letterSpacing: 1
                        }
                    }
                }

                Rectangle { width: 1; height: 24; color: window.isDark ? "#1B3350" : "#CBD5E1" }

                Repeater {
                    model: [
                        {"k": "UPTIME", "v": stats && stats.uptime ? stats.uptime : "--"},
                        {"k": "PROCESSOS", "v": stats && stats.processes ? ("" + stats.processes) : "--"},
                        {"k": "USUÁRIO", "v": jarvisBackend.userName},
                        {"k": "SINCRONIZAÇÃO", "v": "ATIVA"}
                    ]
                    delegate: Column {
                        anchors.verticalCenter: parent.verticalCenter
                        spacing: 2
                        Text { text: modelData.k; color: textMuted; font.pixelSize: 8; font.letterSpacing: 1.3 }
                        Text { text: modelData.v; color: textPrimary; font.pixelSize: 11; font.weight: Font.Medium }
                    }
                }

                Item { Layout.fillWidth: true }

                Text {
                    text: "PRIVACIDADE LOCAL  //  DADOS SOB SEU CONTROLE"
                    color: cyan
                    opacity: window.isDark ? 0.55 : 0.85
                    font.pixelSize: 8
                    font.letterSpacing: 1.4
                }
            }
        }
    }

    // ============================================================ AJUSTES
    Popup {
        id: settingsDialog
        parent: Overlay.overlay
        anchors.centerIn: parent
        width: Math.min(window.width - 80, 920)
        height: Math.min(window.height - 40, 850)
        modal: true
        focus: true
        padding: 0
        closePolicy: Popup.CloseOnEscape

        property int tab: 0

        function selectValue(box, value) {
            var found = box.find(value)
            box.currentIndex = found >= 0 ? found : 0
        }

        function refreshVoiceOptions() {
            voiceModelBox.model = jarvisBackend.voiceModels(voiceEngineBox.currentText)
            voiceNameBox.model = jarvisBackend.voiceNames(voiceEngineBox.currentText)
            voiceModelBox.currentIndex = 0
            voiceNameBox.currentIndex = 0
        }

        function providerNeedsApiKey() {
            return aiProviderBox.currentText === "OpenAI"
                    || aiProviderBox.currentText === "Claude"
                    || aiProviderBox.currentText === "Gemini"
        }

        function loadPermissions() {
            permAgentEnabled.checked = jarvisBackend.agentEnabled
            permFsRead.checked = jarvisBackend.agentFilesystemRead
            permFsWrite.checked = jarvisBackend.agentFilesystemWrite
            permShell.checked = jarvisBackend.agentShell
            permBrowser.checked = jarvisBackend.agentBrowser
            permSsh.checked = jarvisBackend.agentSsh
            permRootsArea.text = jarvisBackend.agentAllowedRoots
        }

        function loadPersona() {
            var p = jarvisBackend.assistantPersona || {}
            pName.text = p.name || "Jarvis"
            function pick(box, val, fallback) {
                var i = box.find(val || fallback)
                box.currentIndex = i >= 0 ? i : 0
            }
            pick(pPersonality, p.personality, "Prestativo e Amigável")
            pick(pTone, p.tone, "Natural")
            pick(pAccent, p.accent, "Português (Brasil)")
            pCustom.text = p.custom_instructions || ""
            mcpForm.reset()
        }

        function loadSettings() {
            loadPermissions()
            loadPersona()
            systemNameField.text = jarvisBackend.systemName
            conversationApiKeyField.clear()
            geminiVoiceApiKeyField.clear()
            weatherCityField.text = jarvisBackend.weatherCity
            webcamSwitch.checked = jarvisBackend.webcamEnabled
            webcamIndexField.text = "" + jarvisBackend.webcamIndex
            selectValue(aiProviderBox, jarvisBackend.selectedAiProvider)
            aiModelBox.model = jarvisBackend.aiModels(aiProviderBox.currentText)
            selectValue(aiModelBox, jarvisBackend.selectedAiModel)
            aiModelBox.editText = jarvisBackend.selectedAiModel
            selectValue(voiceEngineBox, jarvisBackend.selectedVoiceEngine)
            voiceModelBox.model = jarvisBackend.voiceModels(voiceEngineBox.currentText)
            voiceNameBox.model = jarvisBackend.voiceNames(voiceEngineBox.currentText)
            selectValue(voiceModelBox, jarvisBackend.selectedVoiceModel)
            selectValue(voiceNameBox, jarvisBackend.selectedVoiceName)
            selectValue(transcriptionEngineBox, jarvisBackend.selectedTranscriptionEngine)
            transcriptionBox.model = jarvisBackend.transcriptionModelsFor(transcriptionEngineBox.currentText)
            selectValue(transcriptionBox, transcriptionEngineBox.currentText === "OpenAI"
                        ? jarvisBackend.selectedTranscriptionModelCloud
                        : jarvisBackend.selectedTranscriptionModel)
            wakeEnabledSwitch.checked = jarvisBackend.wakeWordEnabled
            wakePhraseField.text = jarvisBackend.wakeWord
            wakeRequiredSwitch.checked = jarvisBackend.wakeWordRequired
            selectValue(voiceSilenceBox, jarvisBackend.selectedVoiceSilenceLabel)
            if (jarvisCloudSettingsPreview) {
                selectValue(aiProviderBox, "OpenAI")
                aiModelBox.model = jarvisBackend.aiModels(aiProviderBox.currentText)
                selectValue(aiModelBox, "gpt-3.5-turbo")
                aiModelBox.editText = "gpt-3.5-turbo"
                selectValue(voiceEngineBox, "Gemini TTS")
                refreshVoiceOptions()
            }
        }

        onOpened: loadSettings()

        Overlay.modal: Rectangle { color: window.isDark ? "#CC020712" : "#80000000" }
        background: Rectangle {
            radius: 18
            color: window.isDark ? "#081122" : "#FFFFFF"
            border.color: window.isDark ? "#26516A" : "#CBD5E1"
            border.width: 1
        }

        contentItem: ColumnLayout {
            anchors.fill: parent
            anchors.margins: 24
            spacing: 14

            RowLayout {
                Layout.fillWidth: true
                Layout.preferredHeight: 54

                Column {
                    spacing: 3
                    Text {
                        text: "CONFIGURAÇÕES DO NÚCLEO"
                        color: textPrimary
                        font.pixelSize: 20
                        font.weight: Font.DemiBold
                        font.letterSpacing: 2
                    }
                    Text {
                        text: "IA, reconhecimento de fala, voz, clima, aparência e permissões"
                        color: textMuted
                        font.pixelSize: 10
                    }
                }

                Item { Layout.fillWidth: true }

                JarvisButton {
                    variant: "close"
                    Layout.preferredWidth: 34
                    Layout.preferredHeight: 34
                    Layout.alignment: Qt.AlignVCenter
                    text: "✕"
                    textSize: 13
                    onClicked: settingsDialog.close()
                }
            }

            Row {
                Layout.fillWidth: true
                Layout.preferredHeight: 36
                Layout.maximumHeight: 36
                spacing: 8

                Repeater {
                    model: [{"t": "GERAL", "i": 0}, {"t": "PERMISSÕES", "i": 1}, {"t": "COMUNICAÇÃO", "i": 2}, {"t": "IDENTIDADE", "i": 3}, {"t": "SETOR", "i": 4}]
                    delegate: Button {
                        width: 118
                        height: 36
                        text: (settingsDialog.tab === modelData.i ? "●  " : "") + modelData.t
                        onClicked: settingsDialog.tab = modelData.i
                        background: Rectangle {
                            radius: 9
                            color: settingsDialog.tab === modelData.i ? (window.isDark ? "#123049" : "#E0F2FE") : (parent.hovered ? (window.isDark ? "#0E1F33" : "#F1F5F9") : "transparent")
                            border.color: settingsDialog.tab === modelData.i ? cyan : (window.isDark ? "#25405A" : "#CBD5E1")
                            opacity: parent.down ? 0.75 : 1
                        }
                        contentItem: Text {
                            text: parent.text
                            color: settingsDialog.tab === modelData.i ? cyan : textMuted
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                            font.pixelSize: 10
                            font.weight: Font.DemiBold
                            font.letterSpacing: 1.2
                        }
                    }
                }
            }

            ScrollView {
                visible: settingsDialog.tab === 0
                Layout.fillWidth: true
                Layout.fillHeight: true
                contentWidth: availableWidth
                clip: true

              ColumnLayout {
                width: parent.width
                spacing: 14

            // ----- card 00: NOME DO SISTEMA
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 104
                radius: 13
                color: window.isDark ? "#0A172B" : "#F8FAFC"
                border.color: window.isDark ? "#183650" : "#CBD5E1"

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 16
                    spacing: 8

                    RowLayout {
                        Layout.fillWidth: true
                        Text { text: "00  IDENTIFICAÇÃO DO SISTEMA"; color: cyan; font.pixelSize: 11; font.weight: Font.DemiBold; font.letterSpacing: 1.3 }
                        Item { Layout.fillWidth: true }
                        Text { text: "Nome exibido na interface e cabeçalhos"; color: textMuted; font.pixelSize: 9 }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 14
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 4
                            Text { text: "NOME DO SISTEMA / ASSISTENTE"; color: textMuted; font.pixelSize: 8; font.letterSpacing: 1.1 }
                            TextField {
                                id: systemNameField
                                Layout.fillWidth: true
                                Layout.preferredHeight: 38
                                text: jarvisBackend.systemName
                                placeholderText: "Ex.: Jarvis, Sexta-Feira, HAL..."
                                placeholderTextColor: window.isDark ? "#526D83" : "#94A3B8"
                                color: textPrimary
                                font.pixelSize: 12
                                leftPadding: 12
                                background: Rectangle {
                                    radius: 9
                                    color: window.isDark ? "#0D1D33" : "#FFFFFF"
                                    border.color: parent.activeFocus ? cyan : (window.isDark ? "#23435E" : "#CBD5E1")
                                }
                            }
                        }
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: settingsDialog.providerNeedsApiKey() ? 214 : 138
                radius: 13
                color: window.isDark ? "#0A172B" : "#F8FAFC"
                border.color: window.isDark ? "#183650" : "#CBD5E1"

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 16
                    spacing: 10

                    RowLayout {
                        Layout.fillWidth: true
                        Text { text: "01  IA DE CONVERSA"; color: cyan; font.pixelSize: 11; font.weight: Font.DemiBold; font.letterSpacing: 1.3 }
                        Item { Layout.fillWidth: true }
                        Text { text: jarvisBackend.credentialHint(aiProviderBox.currentText); color: textMuted; font.pixelSize: 9 }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 14
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 6
                            Text { text: "PROVEDOR"; color: textMuted; font.pixelSize: 8; font.letterSpacing: 1.1 }
                            FuturisticCombo {
                                id: aiProviderBox
                                Layout.fillWidth: true
                                model: jarvisBackend.aiProviders
                                onActivated: {
                                    aiModelBox.model = jarvisBackend.aiModels(currentText)
                                    aiModelBox.currentIndex = 0
                                    aiModelBox.editText = aiModelBox.currentText
                                }
                            }
                        }
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 6
                            RowLayout {
                                Layout.fillWidth: true
                                Text { text: "MODELO"; color: textMuted; font.pixelSize: 8; font.letterSpacing: 1.1 }
                                Item { Layout.fillWidth: true }
                                Text {
                                    text: "digite o nome exato carregado no seu app"
                                    color: textMuted; font.pixelSize: 8
                                    visible: aiProviderBox.currentText === "LM Studio" || aiProviderBox.currentText === "Ollama"
                                }
                            }
                            FuturisticCombo {
                                id: aiModelBox
                                Layout.fillWidth: true
                                editable: true
                                model: jarvisBackend.aiModels(aiProviderBox.currentText)
                            }
                        }
                    }

                    Rectangle {
                        visible: settingsDialog.providerNeedsApiKey()
                        Layout.fillWidth: true
                        Layout.preferredHeight: visible ? 1 : 0
                        color: window.isDark ? "#183650" : "#E2E8F0"
                    }

                    ColumnLayout {
                        visible: settingsDialog.providerNeedsApiKey()
                        Layout.fillWidth: true
                        spacing: 6

                        RowLayout {
                            Layout.fillWidth: true
                            Text {
                                text: jarvisBackend.apiKeyEnvName(aiProviderBox.currentText)
                                color: textMuted
                                font.pixelSize: 8
                                font.letterSpacing: 1.1
                            }
                            Item { Layout.fillWidth: true }
                            Text {
                                property int revision: jarvisBackend.settingsRevision
                                text: {
                                    var sync = revision
                                    return jarvisBackend.apiKeyConfigured(aiProviderBox.currentText) ? "CONFIGURADA" : "NÃO CONFIGURADA"
                                }
                                color: {
                                    var sync = revision
                                    return jarvisBackend.apiKeyConfigured(aiProviderBox.currentText) ? "#4EF2A6" : "#F6C453"
                                }
                                font.pixelSize: 8
                                font.weight: Font.DemiBold
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10

                            TextField {
                                id: conversationApiKeyField
                                Layout.fillWidth: true
                                Layout.preferredHeight: 42
                                echoMode: TextInput.Password
                                passwordCharacter: "*"
                                placeholderText: jarvisBackend.apiKeyConfigured(aiProviderBox.currentText) ? "Chave protegida; digite apenas para substituir" : "Cole aqui a chave do provedor selecionado"
                                placeholderTextColor: window.isDark ? "#526D83" : "#94A3B8"
                                color: textPrimary
                                selectByMouse: true
                                font.pixelSize: 11
                                background: Rectangle {
                                    radius: 9
                                    color: window.isDark ? "#0D1D33" : "#FFFFFF"
                                    border.color: parent.activeFocus ? cyan : (window.isDark ? "#23435E" : "#CBD5E1")
                                }
                                leftPadding: 13
                                rightPadding: 13
                            }

                            JarvisButton {
                                Layout.preferredWidth: 140
                                Layout.preferredHeight: 42
                                text: "🔑  OBTER API KEY"
                                textSize: 9
                                onClicked: jarvisBackend.openApiKeyPage(aiProviderBox.currentText)
                                ToolTip.visible: hovered
                                ToolTip.text: "Abrir a página oficial de chaves do provedor"
                            }

                            JarvisButton {
                                variant: "danger"
                                property int revision: jarvisBackend.settingsRevision
                                visible: {
                                    var sync = revision
                                    return jarvisBackend.apiKeyConfigured(aiProviderBox.currentText)
                                }
                                Layout.preferredWidth: 106
                                Layout.preferredHeight: 42
                                text: "✕  REMOVER"
                                textSize: 9
                                onClicked: {
                                    jarvisBackend.removeApiKey(aiProviderBox.currentText)
                                    conversationApiKeyField.clear()
                                }
                            }
                        }
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: voiceEngineBox.currentText === "Gemini TTS" ? 266 : 194
                radius: 13
                color: window.isDark ? "#0A172B" : "#F8FAFC"
                border.color: window.isDark ? "#183650" : "#CBD5E1"

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 16
                    spacing: 10

                    RowLayout {
                        Layout.fillWidth: true
                        Text { text: "02  VOZ DA RESPOSTA"; color: violet; font.pixelSize: 11; font.weight: Font.DemiBold; font.letterSpacing: 1.3 }
                        Item { Layout.fillWidth: true }
                        Text { text: jarvisBackend.credentialHint(voiceEngineBox.currentText); color: textMuted; font.pixelSize: 9 }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 14
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 6
                            Text { text: "MOTOR DE VOZ"; color: textMuted; font.pixelSize: 8; font.letterSpacing: 1.1 }
                            FuturisticCombo {
                                id: voiceEngineBox
                                Layout.fillWidth: true
                                model: jarvisBackend.voiceEngines
                                onActivated: settingsDialog.refreshVoiceOptions()
                            }
                        }
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 6
                            Text { text: "MODELO TTS"; color: textMuted; font.pixelSize: 8; font.letterSpacing: 1.1 }
                            FuturisticCombo {
                                id: voiceModelBox
                                Layout.fillWidth: true
                                model: jarvisBackend.voiceModels(voiceEngineBox.currentText)
                            }
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 6
                        Text { text: "PERSONALIDADE / VOZ"; color: textMuted; font.pixelSize: 8; font.letterSpacing: 1.1 }
                        FuturisticCombo {
                            id: voiceNameBox
                            Layout.fillWidth: true
                            model: jarvisBackend.voiceNames(voiceEngineBox.currentText)
                        }
                    }

                    Rectangle {
                        visible: voiceEngineBox.currentText === "Gemini TTS"
                        Layout.fillWidth: true
                        Layout.preferredHeight: visible ? 1 : 0
                        color: window.isDark ? "#183650" : "#E2E8F0"
                    }

                    ColumnLayout {
                        visible: voiceEngineBox.currentText === "Gemini TTS"
                        Layout.fillWidth: true
                        spacing: 6

                        RowLayout {
                            Layout.fillWidth: true
                            Text { text: "GEMINI API KEY"; color: textMuted; font.pixelSize: 8; font.letterSpacing: 1.1 }
                            Item { Layout.fillWidth: true }
                            Text {
                                property int revision: jarvisBackend.settingsRevision
                                text: {
                                    var sync = revision
                                    return jarvisBackend.apiKeyConfigured("Gemini TTS") ? "CONFIGURADA" : "NÃO CONFIGURADA"
                                }
                                color: {
                                    var sync = revision
                                    return jarvisBackend.apiKeyConfigured("Gemini TTS") ? "#4EF2A6" : "#F6C453"
                                }
                                font.pixelSize: 8
                                font.weight: Font.DemiBold
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10

                            TextField {
                                id: geminiVoiceApiKeyField
                                Layout.fillWidth: true
                                Layout.preferredHeight: 42
                                echoMode: TextInput.Password
                                passwordCharacter: "*"
                                placeholderText: jarvisBackend.apiKeyConfigured("Gemini TTS") ? "Chave protegida; digite apenas para substituir" : "Cole aqui sua chave do Google AI Studio"
                                placeholderTextColor: window.isDark ? "#526D83" : "#94A3B8"
                                color: textPrimary
                                selectByMouse: true
                                font.pixelSize: 11
                                background: Rectangle {
                                    radius: 9
                                    color: window.isDark ? "#0D1D33" : "#FFFFFF"
                                    border.color: parent.activeFocus ? cyan : (window.isDark ? "#23435E" : "#CBD5E1")
                                }
                                leftPadding: 13
                                rightPadding: 13
                            }

                            JarvisButton {
                                Layout.preferredWidth: 140
                                Layout.preferredHeight: 42
                                text: "🔑  OBTER API KEY"
                                textSize: 9
                                onClicked: jarvisBackend.openApiKeyPage("Gemini TTS")
                                ToolTip.visible: hovered
                                ToolTip.text: "Abrir o Google AI Studio"
                            }

                            JarvisButton {
                                variant: "danger"
                                property int revision: jarvisBackend.settingsRevision
                                visible: {
                                    var sync = revision
                                    return jarvisBackend.apiKeyConfigured("Gemini TTS")
                                }
                                Layout.preferredWidth: 106
                                Layout.preferredHeight: 42
                                text: "✕  REMOVER"
                                textSize: 9
                                onClicked: {
                                    jarvisBackend.removeApiKey("Gemini TTS")
                                    geminiVoiceApiKeyField.clear()
                                }
                            }
                        }
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 334
                radius: 13
                color: window.isDark ? "#0A172B" : "#F8FAFC"
                border.color: window.isDark ? "#183650" : "#CBD5E1"

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 14
                    spacing: 10

                    Text { text: "03  RECONHECIMENTO DE FALA"; color: "#4EF2A6"; font.pixelSize: 11; font.weight: Font.DemiBold; font.letterSpacing: 1.3 }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 14
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 5
                            Text { text: "MOTOR"; color: textMuted; font.pixelSize: 8; font.letterSpacing: 1.1 }
                            FuturisticCombo {
                                id: transcriptionEngineBox
                                Layout.fillWidth: true
                                model: jarvisBackend.transcriptionEngines
                                onActivated: {
                                    transcriptionBox.model = jarvisBackend.transcriptionModelsFor(currentText)
                                    transcriptionBox.currentIndex = 0
                                }
                            }
                        }
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 5
                            Text {
                                text: transcriptionEngineBox.currentText === "OpenAI" ? "MODELO (OPENAI)" : "MODELO (LOCAL)"
                                color: textMuted; font.pixelSize: 8; font.letterSpacing: 1.1
                            }
                            FuturisticCombo {
                                id: transcriptionBox
                                Layout.fillWidth: true
                                model: jarvisBackend.transcriptionModelsFor(transcriptionEngineBox.currentText)
                            }
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 14
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 3
                            Text { text: "TOLERÂNCIA DE PAUSA (SILÊNCIO)"; color: textMuted; font.pixelSize: 8; font.letterSpacing: 1.1 }
                            Text { text: "Tempo que a IA espera você pensar antes de enviar sua pergunta."; color: textMuted; font.pixelSize: 9 }
                        }
                        FuturisticCombo {
                            id: voiceSilenceBox
                            Layout.preferredWidth: 200
                            model: ["Normal (2.5s)", "Confortável (3.5s)", "Longo / Pensativo (5.0s)", "Manual (só no clique)"]
                        }
                    }

                    Text {
                        text: transcriptionEngineBox.currentText === "OpenAI"
                              ? "Manda o áudio pra OpenAI (usa a OPENAI_API_KEY). Mais preciso, ~US$ 0,006/min."
                              : "Whisper local, offline e grátis. 'small' é o recomendado."
                        color: textMuted; font.pixelSize: 9; wrapMode: Text.Wrap; Layout.fillWidth: true
                    }

                    Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: window.isDark ? "#183650" : "#E2E8F0" }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 16
                        Column {
                            Layout.preferredWidth: 260
                            spacing: 4
                            Text { text: "PALAVRA DE ATIVAÇÃO"; color: textMuted; font.pixelSize: 8; font.letterSpacing: 1.1 }
                            Text { text: "Escuta o microfone e ativa a voz ao ouvir a palavra."; color: textMuted; font.pixelSize: 9; width: 250; wrapMode: Text.Wrap }
                        }
                        TextField {
                            id: wakePhraseField
                            Layout.fillWidth: true
                            Layout.preferredHeight: 40
                            enabled: wakeEnabledSwitch.checked
                            placeholderText: "jarvis"
                            placeholderTextColor: window.isDark ? "#526D83" : "#94A3B8"
                            color: textPrimary
                            selectByMouse: true
                            font.pixelSize: 12
                            leftPadding: 12
                            background: Rectangle {
                                radius: 9
                                color: wakePhraseField.enabled ? (window.isDark ? "#0D1D33" : "#FFFFFF") : (window.isDark ? "#0A1526" : "#F1F5F9")
                                border.color: wakePhraseField.activeFocus ? cyan : (window.isDark ? "#23435E" : "#CBD5E1")
                            }
                        }
                        Switch { id: wakeEnabledSwitch }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 16
                        enabled: wakeEnabledSwitch.checked
                        Column {
                            Layout.fillWidth: true
                            spacing: 4
                            Text { text: "EXIGIR O NOME EM TODA MENSAGEM"; color: textMuted; font.pixelSize: 8; font.letterSpacing: 1.1 }
                            Text { text: "Só responde se você começar com a palavra (voz e texto). Ex.: \"jarvis, abra o D:\"."; color: textMuted; font.pixelSize: 9; width: 320; wrapMode: Text.Wrap }
                        }
                        Switch { id: wakeRequiredSwitch }
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 118
                radius: 13
                color: window.isDark ? "#0A172B" : "#F8FAFC"
                border.color: window.isDark ? "#183650" : "#CBD5E1"

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 16
                    spacing: 8

                    Text { text: "04  CLIMA"; color: "#F6C453"; font.pixelSize: 11; font.weight: Font.DemiBold; font.letterSpacing: 1.3 }
                    Text {
                        text: "Cidade usada no cartão de clima do HUB (Open-Meteo, sem chave)."
                        color: textMuted; font.pixelSize: 9; Layout.fillWidth: true; wrapMode: Text.Wrap
                    }
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 10
                        Text { text: "CIDADE"; color: textMuted; font.pixelSize: 8; font.letterSpacing: 1.1 }
                        TextField {
                            id: weatherCityField
                            Layout.fillWidth: true
                            Layout.preferredHeight: 40
                            placeholderText: "São Paulo"
                            placeholderTextColor: window.isDark ? "#526D83" : "#94A3B8"
                            color: textPrimary
                            selectByMouse: true
                            font.pixelSize: 12
                            leftPadding: 12
                            background: Rectangle {
                                radius: 9
                                color: window.isDark ? "#0D1D33" : "#FFFFFF"
                                border.color: parent.activeFocus ? cyan : (window.isDark ? "#23435E" : "#CBD5E1")
                            }
                        }
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 176
                radius: 13
                color: window.isDark ? "#0A172B" : "#F8FAFC"
                border.color: window.isDark ? "#183650" : "#CBD5E1"

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 16
                    spacing: 8

                    RowLayout {
                        Layout.fillWidth: true
                        Text { text: "05  WEBCAM (VISÃO)"; color: "#A98BFF"; font.pixelSize: 11; font.weight: Font.DemiBold; font.letterSpacing: 1.3 }
                        Item { Layout.fillWidth: true }
                        Text {
                            text: jarvisBackend.webcamSupported ? "" : "pacote .[vision] ausente"
                            color: amber; font.pixelSize: 9
                        }
                    }
                    Text {
                        text: "Deixa a IA enxergar pela sua webcam quando você pedir (\"o que você está vendo?\"). "
                              + "A imagem só vai para o provedor de IA que você escolheu. Desligado por padrão."
                        color: textMuted; font.pixelSize: 9; Layout.fillWidth: true; wrapMode: Text.Wrap
                    }
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 14
                        Column {
                            Layout.fillWidth: true
                            spacing: 3
                            Text { text: "HABILITAR VISÃO PELA WEBCAM"; color: textMuted; font.pixelSize: 8; font.letterSpacing: 1.1 }
                            Text { text: "Com o Agente ligado, vira a ferramenta 'ver_pela_webcam'."; color: textMuted; font.pixelSize: 9 }
                        }
                        Switch { id: webcamSwitch; enabled: jarvisBackend.webcamSupported }
                    }
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 10
                        enabled: webcamSwitch.checked
                        Text { text: "CÂMERA Nº"; color: textMuted; font.pixelSize: 8; font.letterSpacing: 1.1 }
                        TextField {
                            id: webcamIndexField
                            Layout.preferredWidth: 70
                            Layout.preferredHeight: 38
                            text: "0"
                            inputMask: "9;_"
                            color: textPrimary; font.pixelSize: 12; leftPadding: 12
                            background: Rectangle { radius: 9; color: window.isDark ? "#0D1D33" : "#FFFFFF"; border.color: parent.activeFocus ? cyan : (window.isDark ? "#23435E" : "#CBD5E1") }
                        }
                        JarvisButton {
                            text: "⚡  TESTAR AGORA"
                            enabled: webcamSwitch.checked && jarvisBackend.webcamSupported
                            textSize: 9
                            onClicked: { webcamTest.reset(); webcamTest.open(); jarvisBackend.testWebcam() }
                        }
                        Item { Layout.fillWidth: true }
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 120
                radius: 13
                color: window.isDark ? "#0A172B" : "#F8FAFC"
                border.color: window.isDark ? "#183650" : "#CBD5E1"

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 16
                    spacing: 8

                    Text { text: "06  APARÊNCIA & TEMA"; color: cyan; font.pixelSize: 11; font.weight: Font.DemiBold; font.letterSpacing: 1.3 }
                    Text {
                        text: "Escolha entre o tema Escuro futurista de alto contraste ou o tema Claro limpo e elegante."
                        color: textMuted; font.pixelSize: 9; Layout.fillWidth: true; wrapMode: Text.Wrap
                    }
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 12
                        JarvisButton {
                            text: "🌙  TEMA ESCURO"
                            variant: window.isDark ? "primary" : "secondary"
                            textSize: 9
                            onClicked: jarvisBackend.setTheme("dark")
                        }
                        JarvisButton {
                            text: "☀️  TEMA CLARO"
                            variant: !window.isDark ? "primary" : "secondary"
                            textSize: 9
                            onClicked: jarvisBackend.setTheme("light")
                        }
                        Item { Layout.fillWidth: true }
                    }
                }
            }

              }
            }

            Rectangle {
                visible: settingsDialog.tab === 1
                Layout.fillWidth: true
                Layout.fillHeight: true
                radius: 13
                color: window.isDark ? "#0A172B" : "#F8FAFC"
                border.color: window.isDark ? "#183650" : "#CBD5E1"

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 16
                    spacing: 10

                    RowLayout {
                        Layout.fillWidth: true
                        Text { text: "05  PERMISSÕES DO AGENTE"; color: "#F6C453"; font.pixelSize: 11; font.weight: Font.DemiBold; font.letterSpacing: 1.3 }
                        Item { Layout.fillWidth: true }
                    }
                    Text {
                        Layout.fillWidth: true
                        text: "Define o que o Jarvis pode fazer no computador. Ele confirma antes de apagar, mover, sobrescrever arquivos ou rodar comandos perigosos."
                        color: textMuted; font.pixelSize: 9; wrapMode: Text.Wrap
                    }

                    component PermToggle : RowLayout {
                        id: permRoot
                        Layout.fillWidth: true
                        property alias checked: pt_switch.checked
                        property alias switchEnabled: pt_switch.enabled
                        property string title
                        property string subtitle
                        Column {
                            Layout.fillWidth: true
                            Text { text: permRoot.title; color: textPrimary; font.pixelSize: 12 }
                            Text { text: permRoot.subtitle; color: textMuted; font.pixelSize: 9 }
                        }
                        Switch { id: pt_switch }
                    }

                    PermToggle {
                        id: permAgentEnabled
                        title: "Ativar o agente"
                        subtitle: "Sem isto, o Jarvis apenas conversa."
                    }
                    PermToggle {
                        id: permFsRead
                        title: "Ler arquivos e pastas"
                        subtitle: "Abrir, listar e procurar conteúdo."
                        switchEnabled: permAgentEnabled.checked
                    }
                    PermToggle {
                        id: permFsWrite
                        title: "Criar e alterar arquivos"
                        subtitle: "Escrever, anexar, criar pasta, mover e apagar."
                        switchEnabled: permAgentEnabled.checked
                    }
                    PermToggle {
                        id: permShell
                        title: "Executar comandos (PowerShell)"
                        subtitle: "Scripts, git e utilitários do Windows."
                        switchEnabled: permAgentEnabled.checked
                    }
                    PermToggle {
                        id: permBrowser
                        title: "Internet"
                        subtitle: "Abrir sites, pesquisar na web e ler páginas."
                        switchEnabled: permAgentEnabled.checked
                    }
                    PermToggle {
                        id: permSsh
                        title: "Acesso SSH a servidores"
                        subtitle: jarvisBackend.sshClientAvailable
                                  ? "Rodar comandos numa VPS. Todo comando pede confirmação."
                                  : "Cliente OpenSSH do Windows não encontrado."
                        switchEnabled: permAgentEnabled.checked && jarvisBackend.sshClientAvailable
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        Layout.topMargin: 2
                        spacing: 4
                        RowLayout {
                            Layout.fillWidth: true
                            Text {
                                Layout.fillWidth: true
                                text: jarvisBackend.servers.length + " servidor(es) cadastrado(s)"
                                color: textMuted; font.pixelSize: 9
                            }
                            JarvisButton {
                                text: "🖥  GERENCIAR SERVIDORES"
                                enabled: jarvisBackend.sshClientAvailable
                                textSize: 9
                                onClicked: serverManager.open()
                            }
                        }
                        Text {
                            Layout.fillWidth: true
                            visible: !permSsh.checked && jarvisBackend.servers.length > 0
                            text: "Servidores salvos, mas o agente só usa SSH com este toggle ligado (ou no perfil Desenvolvimento)."
                            color: "#F6C453"; font.pixelSize: 8; wrapMode: Text.Wrap
                        }
                    }

                    Text { text: "PASTAS ONDE PODE ESCREVER (uma por linha)"; color: textMuted; font.pixelSize: 8; font.letterSpacing: 1.1 }
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        Layout.minimumHeight: 70
                        radius: 9
                        color: window.isDark ? "#0D1D33" : "#FFFFFF"
                        border.color: window.isDark ? "#23435E" : "#CBD5E1"
                        ScrollView {
                            anchors.fill: parent
                            anchors.margins: 8
                            TextArea {
                                id: permRootsArea
                                color: textPrimary
                                font.pixelSize: 11
                                wrapMode: TextArea.NoWrap
                                placeholderText: "C:/Users/você/Documentos\nD:/Projetos"
                                placeholderTextColor: window.isDark ? "#526D83" : "#94A3B8"
                                background: null
                            }
                        }
                    }
                    Text {
                        text: "Vazio = o Jarvis só escreve dentro da sua pasta de usuário."
                        color: textMuted; font.pixelSize: 9
                    }
                }
            }

            // ========================================== ABA 2: COMUNICAÇÃO (CANAIS / WHATSAPP)
            ScrollView {
                visible: settingsDialog.tab === 2
                Layout.fillWidth: true
                Layout.fillHeight: true
                contentWidth: availableWidth
                clip: true

                ColumnLayout {
                    width: parent.width
                    spacing: 16

                    // Header: CANAIS / Conexões / Subtitle / + Nova conexão
                    RowLayout {
                        Layout.fillWidth: true
                        Column {
                            spacing: 2
                            Text {
                                text: "CANAIS"
                                color: green
                                font.pixelSize: 9
                                font.weight: Font.Bold
                                font.letterSpacing: 1.5
                            }
                            Text {
                                text: "Conexões"
                                color: textPrimary
                                font.pixelSize: 18
                                font.weight: Font.DemiBold
                                font.letterSpacing: 1.1
                            }
                            Text {
                                text: "Conecte números do WhatsApp por QR Code e acompanhe o estado de cada canal."
                                color: textMuted
                                font.pixelSize: 10
                            }
                        }
                        Item { Layout.fillWidth: true }
                        JarvisButton {
                            variant: "success"
                            text: "+  Nova conexão"
                            implicitHeight: 38
                            leftPadding: 16; rightPadding: 16
                            onClicked: {
                                whatsappQrModal.open()
                                jarvisBackend.connectWhatsApp()
                            }
                        }
                    }

                    // Metric / Stats Bar
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 64
                        radius: 12
                        color: window.isDark ? "#0A1526" : "#F8FAFC"
                        border.color: window.isDark ? "#183650" : "#CBD5E1"

                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: 20
                            anchors.rightMargin: 20
                            spacing: 20

                            // Metric 1: Total de conexões
                            Row {
                                spacing: 12
                                Rectangle {
                                    width: 36; height: 36; radius: 18
                                    color: window.isDark ? "#123049" : "#E0F2FE"
                                    anchors.verticalCenter: parent.verticalCenter
                                    Text { anchors.centerIn: parent; text: "📡"; font.pixelSize: 15 }
                                }
                                Column {
                                    anchors.verticalCenter: parent.verticalCenter
                                    spacing: 2
                                    Text { text: "Total de conexões"; color: textMuted; font.pixelSize: 9 }
                                    Text {
                                        text: jarvisBackend.whatsappConnected ? "1" : (jarvisBackend.whatsappStatus !== "disconnected" ? "1" : "0")
                                        color: textPrimary
                                        font.pixelSize: 14
                                        font.weight: Font.Bold
                                    }
                                }
                            }

                            Rectangle { width: 1; height: 30; color: window.isDark ? "#1C3650" : "#E2E8F0" }

                            // Metric 2: Conectadas
                            Row {
                                spacing: 12
                                Rectangle {
                                    width: 36; height: 36; radius: 18
                                    color: window.isDark ? "#0C2E20" : "#DCFCE7"
                                    anchors.verticalCenter: parent.verticalCenter
                                    Text { anchors.centerIn: parent; text: "🛜"; font.pixelSize: 15 }
                                }
                                Column {
                                    anchors.verticalCenter: parent.verticalCenter
                                    spacing: 2
                                    Text { text: "Conectadas"; color: textMuted; font.pixelSize: 9 }
                                    Text {
                                        text: jarvisBackend.whatsappConnected ? "1" : "0"
                                        color: textPrimary
                                        font.pixelSize: 14
                                        font.weight: Font.Bold
                                    }
                                }
                            }

                            Item { Layout.fillWidth: true }

                            JarvisButton {
                                variant: "secondary"
                                text: "↻  Atualizar"
                                implicitHeight: 32
                                leftPadding: 12; rightPadding: 12
                                textSize: 8
                                onClicked: {
                                    jarvisBackend.whatsappLogsChanged()
                                    jarvisBackend.whatsappStatusChanged()
                                }
                            }
                        }
                    }

                    // Grid / Card de Conexão WhatsApp
                    Flow {
                        Layout.fillWidth: true
                        spacing: 16

                        // Card quando conectado (modelo idêntico ao anexo)
                        Rectangle {
                            visible: jarvisBackend.whatsappConnected
                            width: 380
                            implicitHeight: connCardCol.implicitHeight + 36
                            radius: 14
                            color: window.isDark ? "#0A172B" : "#FFFFFF"
                            border.color: window.isDark ? "#18503C" : "#86EFAC"
                            border.width: 1.5

                            ColumnLayout {
                                id: connCardCol
                                anchors.fill: parent
                                anchors.margins: 18
                                spacing: 12

                                // Top row do card: Ícone WhatsApp + Título + Badge Padrão
                                RowLayout {
                                    Layout.fillWidth: true
                                    spacing: 12

                                    Rectangle {
                                        width: 38; height: 38; radius: 10
                                        color: window.isDark ? "#0C2E20" : "#DCFCE7"
                                        border.color: window.isDark ? "#1E824C" : "#86EFAC"
                                        Text { anchors.centerIn: parent; text: "💬"; font.pixelSize: 17 }
                                    }

                                    Column {
                                        Layout.fillWidth: true
                                        spacing: 2
                                        Text {
                                            text: jarvisBackend.whatsappUserName || "WhatsApp Principal"
                                            color: textPrimary
                                            font.pixelSize: 13
                                            font.weight: Font.DemiBold
                                            elide: Text.ElideRight
                                        }
                                        Text {
                                            text: "WhatsApp via QR Code"
                                            color: textMuted
                                            font.pixelSize: 9
                                        }
                                    }

                                    Rectangle {
                                        implicitHeight: 22
                                        implicitWidth: 64
                                        radius: 11
                                        color: window.isDark ? "#0E2822" : "#E6F4EA"
                                        border.color: window.isDark ? "#1E824C" : "#A8DAB5"
                                        Row {
                                            anchors.centerIn: parent
                                            spacing: 4
                                            Text { text: "🛡"; font.pixelSize: 8; color: green; anchors.verticalCenter: parent.verticalCenter }
                                            Text { text: "Padrão"; font.pixelSize: 8; font.weight: Font.DemiBold; color: green; anchors.verticalCenter: parent.verticalCenter }
                                        }
                                    }
                                }

                                // Status Box (Verde)
                                Rectangle {
                                    Layout.fillWidth: true
                                    implicitHeight: 52
                                    radius: 10
                                    color: window.isDark ? "#071C17" : "#F0FDF4"
                                    border.color: window.isDark ? "#144D38" : "#BBF7D0"

                                    ColumnLayout {
                                        anchors.fill: parent
                                        anchors.leftMargin: 12
                                        anchors.rightMargin: 12
                                        spacing: 2
                                        Row {
                                            spacing: 6
                                            Rectangle { width: 7; height: 7; radius: 4; color: green; anchors.verticalCenter: parent.verticalCenter }
                                            Text { text: "Conectada"; color: green; font.pixelSize: 10; font.weight: Font.DemiBold; anchors.verticalCenter: parent.verticalCenter }
                                        }
                                        Text {
                                            text: "Canal disponível para os próximos passos do atendimento"
                                            color: window.isDark ? "#8BF7C2" : "#166534"
                                            font.pixelSize: 8
                                        }
                                    }
                                }

                                // Detalhes (Número e Grupos)
                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 8

                                    RowLayout {
                                        Layout.fillWidth: true
                                        Text { text: "📱  Número"; color: textMuted; font.pixelSize: 9; Layout.preferredWidth: 100 }
                                        Text { text: "+" + jarvisBackend.whatsappUserPhone; color: textPrimary; font.pixelSize: 10; font.weight: Font.DemiBold; Layout.fillWidth: true; horizontalAlignment: Text.AlignRight }
                                    }
                                    RowLayout {
                                        Layout.fillWidth: true
                                        Text { text: "👥  Grupos"; color: textMuted; font.pixelSize: 9; Layout.preferredWidth: 100 }
                                        Text { text: "Todos"; color: textPrimary; font.pixelSize: 10; font.weight: Font.Medium; Layout.fillWidth: true; horizontalAlignment: Text.AlignRight }
                                    }
                                }

                                Rectangle { Layout.fillWidth: true; height: 1; color: window.isDark ? "#152A42" : "#E2E8F0" }

                                // Bottom Actions Row
                                RowLayout {
                                    Layout.fillWidth: true
                                    spacing: 8

                                    JarvisButton {
                                        variant: "secondary"
                                        text: "🔌  Desconectar"
                                        implicitHeight: 32
                                        leftPadding: 10; rightPadding: 10
                                        textSize: 8
                                        onClicked: jarvisBackend.disconnectWhatsApp()
                                    }

                                    Item { Layout.fillWidth: true }

                                    JarvisButton {
                                        variant: "secondary"
                                        text: "✎"
                                        width: 32; height: 32
                                        textSize: 11
                                        ToolTip.visible: hovered
                                        ToolTip.text: "Editar nome do canal"
                                        ToolTip.delay: 300
                                    }

                                    JarvisButton {
                                        variant: "danger"
                                        text: "🗑"
                                        width: 32; height: 32
                                        textSize: 11
                                        ToolTip.visible: hovered
                                        ToolTip.text: "Remover conexão"
                                        ToolTip.delay: 300
                                        onClicked: jarvisBackend.disconnectWhatsApp()
                                    }
                                }
                            }
                        }

                        // Card quando Desconectado (Estado Vazio)
                        Rectangle {
                            visible: !jarvisBackend.whatsappConnected
                            Layout.fillWidth: true
                            implicitHeight: 180
                            radius: 14
                            color: window.isDark ? "#0A172B" : "#F8FAFC"
                            border.color: window.isDark ? "#183650" : "#CBD5E1"

                            ColumnLayout {
                                anchors.centerIn: parent
                                spacing: 12

                                Rectangle {
                                    width: 48; height: 48; radius: 24
                                    color: window.isDark ? "#123049" : "#E0F2FE"
                                    Layout.alignment: Qt.AlignHCenter
                                    Text { anchors.centerIn: parent; text: "💬"; font.pixelSize: 22 }
                                }

                                Text {
                                    text: "Nenhuma conexão do WhatsApp ativa no momento"
                                    color: textPrimary
                                    font.pixelSize: 12
                                    font.weight: Font.DemiBold
                                    Layout.alignment: Qt.AlignHCenter
                                }

                                Text {
                                    text: "Clique no botão abaixo para gerar o QR Code e conectar o seu número."
                                    color: textMuted
                                    font.pixelSize: 9
                                    Layout.alignment: Qt.AlignHCenter
                                }

                                JarvisButton {
                                    variant: "success"
                                    text: "+  Nova conexão via QR Code"
                                    Layout.alignment: Qt.AlignHCenter
                                    implicitHeight: 36
                                    onClicked: {
                                        whatsappQrModal.open()
                                        jarvisBackend.connectWhatsApp()
                                    }
                                }
                            }
                        }
                    }
                }
            }

            // ================================================ ABA 3: IDENTIDADE
            ScrollView {
                visible: settingsDialog.tab === 3
                Layout.fillWidth: true
                Layout.fillHeight: true
                contentWidth: availableWidth
                clip: true

                ColumnLayout {
                    width: parent.width
                    spacing: 16

                    // ---- Persona
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 402
                        radius: 13
                        color: window.isDark ? "#0A172B" : "#F8FAFC"
                        border.color: window.isDark ? "#183650" : "#E2E8F0"

                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 16
                            spacing: 12

                            Text { text: "06  PERSONALIZAÇÃO"; color: "#F6C453"; font.pixelSize: 11; font.weight: Font.DemiBold; font.letterSpacing: 1.3 }
                            Text {
                                Layout.fillWidth: true
                                text: "Nome, jeito de falar e sotaque. É assim que ele se apresenta e interage com você. A voz é ajustada na aba GERAL."
                                color: textMuted; font.pixelSize: 9; wrapMode: Text.Wrap
                            }

                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 12
                                ColumnLayout {
                                    Layout.preferredWidth: 190
                                    spacing: 4
                                    Text { text: "NOME DO ASSISTENTE"; color: textMuted; font.pixelSize: 8; font.letterSpacing: 1.1 }
                                    TextField {
                                        id: pName
                                        Layout.fillWidth: true; Layout.preferredHeight: 40
                                        placeholderText: "Jarvis"
                                        color: textPrimary; font.pixelSize: 13; leftPadding: 12
                                        background: Rectangle { radius: 9; color: window.isDark ? "#0D1D33" : "#FFFFFF"; border.color: parent.activeFocus ? cyan : (window.isDark ? "#23435E" : "#CBD5E1") }
                                    }
                                }
                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 4
                                    Text { text: "TONALIDADE"; color: textMuted; font.pixelSize: 8; font.letterSpacing: 1.1 }
                                    FuturisticCombo {
                                        id: pTone
                                        Layout.fillWidth: true; Layout.preferredHeight: 40
                                        model: jarvisBackend.toneOptions
                                    }
                                }
                            }

                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 12
                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 4
                                    Text { text: "PERSONALIDADE"; color: textMuted; font.pixelSize: 8; font.letterSpacing: 1.1 }
                                    FuturisticCombo {
                                        id: pPersonality
                                        Layout.fillWidth: true; Layout.preferredHeight: 40
                                        model: jarvisBackend.personalityOptions
                                    }
                                }
                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 4
                                    Text { text: "SOTAQUE / IDIOMA"; color: textMuted; font.pixelSize: 8; font.letterSpacing: 1.1 }
                                    FuturisticCombo {
                                        id: pAccent
                                        Layout.fillWidth: true; Layout.preferredHeight: 40
                                        model: jarvisBackend.accentOptions
                                    }
                                }
                            }

                            Text { text: "INSTRUÇÕES EXTRAS (opcional)"; color: textMuted; font.pixelSize: 8; font.letterSpacing: 1.1 }
                            Rectangle {
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                radius: 9
                                color: window.isDark ? "#0D1D33" : "#FFFFFF"
                                border.color: pCustom.activeFocus ? cyan : (window.isDark ? "#23435E" : "#CBD5E1")
                                ScrollView {
                                    anchors.fill: parent
                                    anchors.margins: 8
                                    clip: true
                                    TextArea {
                                        id: pCustom
                                        color: textPrimary; font.pixelSize: 11
                                        wrapMode: TextArea.Wrap
                                        placeholderText: "Ex.: responda sempre em português, seja conciso, me chame de chefe, não use emojis..."
                                        placeholderTextColor: window.isDark ? "#526D83" : "#94A3B8"
                                        background: null
                                    }
                                }
                            }
                            Text {
                                Layout.fillWidth: true
                                text: "A palavra de ativação por voz continua sendo \"" + (wakePhraseField.text || "Jarvis") + "\" — ajuste em GERAL se quiser trocar."
                                color: textMuted; font.pixelSize: 8; wrapMode: Text.Wrap
                            }
                        }
                    }

                    // ---- MCP
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 176 + mcpList.implicitHeight
                                                + (mcpForm.visible ? mcpForm.implicitHeight + 10 : 0)
                                                + (mcpTestWrap.visible ? mcpTestWrap.Layout.preferredHeight + 10 : 0)
                        radius: 13
                        color: window.isDark ? "#0A172B" : "#F8FAFC"
                        border.color: window.isDark ? "#183650" : "#E2E8F0"

                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 16
                            spacing: 10

                            RowLayout {
                                Layout.fillWidth: true
                                Text { text: "07  FERRAMENTAS EXTERNAS (MCP)"; color: "#F6C453"; font.pixelSize: 11; font.weight: Font.DemiBold; font.letterSpacing: 1.3; Layout.fillWidth: true }
                                JarvisButton {
                                    variant: "secondary"; text: mcpForm.editId >= 0 ? "✕ FECHAR" : "+ SERVIDOR"
                                    implicitHeight: 28
                                    onClicked: mcpForm.editId >= 0 ? mcpForm.reset() : mcpForm.openNew()
                                }
                            }
                            Text {
                                Layout.fillWidth: true
                                text: "Conecte servidores Model Context Protocol (stdio). As ferramentas deles ficam disponíveis para o agente com o prefixo mcp_. Ex.: comando 'npx', args [\"-y\",\"@modelcontextprotocol/server-filesystem\",\"D:/\"]."
                                color: textMuted; font.pixelSize: 9; wrapMode: Text.Wrap
                            }

                            ColumnLayout {
                                id: mcpList
                                Layout.fillWidth: true
                                spacing: 6
                                Repeater {
                                    model: jarvisBackend.mcpServers || []
                                    delegate: Rectangle {
                                        Layout.fillWidth: true
                                        Layout.preferredHeight: 44
                                        radius: 9
                                        color: window.isDark ? "#0C1E33" : "#FFFFFF"
                                        border.color: window.isDark ? "#23435E" : "#E2E8F0"
                                        RowLayout {
                                            anchors.fill: parent
                                            anchors.leftMargin: 12; anchors.rightMargin: 8
                                            spacing: 8
                                            Rectangle { width: 7; height: 7; radius: 4; color: modelData.enabled ? green : "#506273" }
                                            ColumnLayout {
                                                Layout.fillWidth: true
                                                spacing: 0
                                                Text { text: modelData.name; color: textPrimary; font.pixelSize: 11; font.weight: Font.DemiBold }
                                                Text { Layout.fillWidth: true; text: (modelData.command + " " + modelData.args); color: textMuted; font.pixelSize: 8; elide: Text.ElideRight }
                                            }
                                            JarvisButton { variant: "secondary"; text: "TESTAR"; implicitHeight: 26; onClicked: { mcpTestBox.text = "testando " + modelData.name + "…"; jarvisBackend.testMcpServer(modelData) } }
                                            JarvisButton { variant: "secondary"; text: "EDITAR"; implicitHeight: 26; onClicked: mcpForm.openEdit(modelData) }
                                            JarvisButton { variant: "danger"; text: "✕"; implicitHeight: 26; onClicked: jarvisBackend.deleteMcpServer(modelData.id) }
                                        }
                                    }
                                }
                                Text {
                                    visible: !jarvisBackend.mcpServers || jarvisBackend.mcpServers.length === 0
                                    text: "Nenhum servidor MCP. Clique em + SERVIDOR."
                                    color: textMuted; font.pixelSize: 10
                                }
                            }

                            ColumnLayout {
                                id: mcpForm
                                Layout.fillWidth: true
                                spacing: 8
                                visible: editId >= 0
                                property int editId: -1
                                function reset() { editId = -1; mName.text=""; mCmd.text=""; mArgs.text=""; mEnv.text=""; mEnabled.checked = true }
                                function openNew() { reset(); editId = 0 }
                                function openEdit(s) { editId = s.id; mName.text = s.name; mCmd.text = s.command; mArgs.text = s.args; mEnv.text = s.env_vars; mEnabled.checked = s.enabled ? true : false }

                                Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: window.isDark ? "#183650" : "#E2E8F0" }
                                RowLayout {
                                    Layout.fillWidth: true; spacing: 10
                                    TextField { id: mName; Layout.preferredWidth: 150; Layout.preferredHeight: 36; placeholderText: "nome (ex.: filesystem)"; color: textPrimary; font.pixelSize: 11; leftPadding: 10; background: Rectangle { radius: 8; color: window.isDark ? "#0D1D33" : "#FFFFFF"; border.color: parent.activeFocus ? cyan : "#23435E" } }
                                    TextField { id: mCmd; Layout.fillWidth: true; Layout.preferredHeight: 36; placeholderText: "comando (npx, uvx, python...)"; color: textPrimary; font.pixelSize: 11; leftPadding: 10; background: Rectangle { radius: 8; color: window.isDark ? "#0D1D33" : "#FFFFFF"; border.color: parent.activeFocus ? cyan : "#23435E" } }
                                    Switch { id: mEnabled; checked: true }
                                }
                                TextField { id: mArgs; Layout.fillWidth: true; Layout.preferredHeight: 36; placeholderText: 'args JSON: ["-y","@modelcontextprotocol/server-filesystem","D:/Projetos"]'; color: textPrimary; font.pixelSize: 10; leftPadding: 10; background: Rectangle { radius: 8; color: window.isDark ? "#0D1D33" : "#FFFFFF"; border.color: parent.activeFocus ? cyan : "#23435E" } }
                                TextField { id: mEnv; Layout.fillWidth: true; Layout.preferredHeight: 36; placeholderText: 'env JSON (opcional): {"API_KEY":"..."}'; color: textPrimary; font.pixelSize: 10; leftPadding: 10; background: Rectangle { radius: 8; color: window.isDark ? "#0D1D33" : "#FFFFFF"; border.color: parent.activeFocus ? cyan : "#23435E" } }
                                RowLayout {
                                    Layout.fillWidth: true
                                    Item { Layout.fillWidth: true }
                                    JarvisButton {
                                        variant: "success"; text: "SALVAR SERVIDOR"; implicitHeight: 30
                                        onClicked: {
                                            jarvisBackend.saveMcpServer(mcpForm.editId, mName.text, mCmd.text, mArgs.text, mEnv.text || "{}", mEnabled.checked)
                                            mcpForm.reset()
                                        }
                                    }
                                }
                            }

                            Rectangle {
                                id: mcpTestWrap
                                Layout.fillWidth: true
                                visible: mcpTestBox.text !== ""
                                Layout.preferredHeight: Math.max(36, mcpTestBox.implicitHeight + 16)
                                radius: 8
                                color: window.isDark ? "#050C18" : "#F1F5F9"
                                border.color: "#1E3B5C"
                                Text {
                                    id: mcpTestBox
                                    anchors.fill: parent; anchors.margins: 8
                                    text: ""
                                    color: window.isDark ? "#CDE4F2" : "#0F172A"; font.family: "Consolas, monospace"; font.pixelSize: 9
                                    wrapMode: Text.Wrap
                                }
                            }

                            Item { Layout.fillHeight: true }

                            Connections {
                                target: jarvisBackend
                                function onMcpTested(r) {
                                    if (r.ok) {
                                        var lines = []
                                        var ts = r.tools || []
                                        for (var i = 0; i < ts.length; i++)
                                            lines.push("  • " + ts[i].name + (ts[i].description ? " — " + ts[i].description : ""))
                                        mcpTestBox.text = "✓ " + (r.server || "") + "  (" + ((r.serverInfo && r.serverInfo.name) || "?") + ")\n"
                                            + ts.length + " ferramenta(s):\n" + lines.join("\n")
                                    } else {
                                        mcpTestBox.text = "✗ falhou: " + (r.error || "erro desconhecido")
                                    }
                                }
                            }
                        }
                    }
                }
            }

            // ================================================ ABA 4: SETOR
            ScrollView {
                visible: settingsDialog.tab === 4
                Layout.fillWidth: true
                Layout.fillHeight: true
                contentWidth: availableWidth
                clip: true

                ColumnLayout {
                    width: parent.width
                    spacing: 14

                    Text { text: "08  SETOR DE ATIVIDADE"; color: "#F6C453"; font.pixelSize: 11; font.weight: Font.DemiBold; font.letterSpacing: 1.3 }
                    Text {
                        Layout.fillWidth: true
                        text: "Escolha o ramo em que você atua. O assistente ganha uma especialização de domínio, esconde telas que não servem pra sua área e mostra atalhos próprios dela. Aplica na hora. É diferente do 'Perfil de uso' (que controla o que o agente pode fazer no PC)."
                        color: textMuted; font.pixelSize: 9; wrapMode: Text.Wrap
                    }

                    GridLayout {
                        Layout.fillWidth: true
                        columns: 3
                        columnSpacing: 8
                        rowSpacing: 8

                        Repeater {
                            model: jarvisBackend.sectorChoices
                            delegate: Rectangle {
                                Layout.fillWidth: true
                                Layout.preferredHeight: 58
                                radius: 10
                                readonly property bool active: jarvisBackend.sector === modelData.id
                                color: active ? (window.isDark ? "#123049" : "#E0F2FE")
                                              : (secMouse.containsMouse ? (window.isDark ? "#0E1F33" : "#F1F5F9") : (window.isDark ? "#0A172B" : "#F8FAFC"))
                                border.color: active ? cyan : (window.isDark ? "#1F3B57" : "#CBD5E1")
                                Row {
                                    anchors.fill: parent
                                    anchors.leftMargin: 12
                                    anchors.rightMargin: 10
                                    spacing: 10
                                    Text { anchors.verticalCenter: parent.verticalCenter; text: modelData.icon; font.pixelSize: 18 }
                                    Column {
                                        anchors.verticalCenter: parent.verticalCenter
                                        width: parent.width - 40
                                        spacing: 1
                                        Text { text: modelData.name; color: active ? cyan : textPrimary; font.pixelSize: 11; font.weight: Font.DemiBold }
                                        Text { text: modelData.tagline; color: textMuted; font.pixelSize: 8; elide: Text.ElideRight; width: parent.width }
                                    }
                                }
                                MouseArea {
                                    id: secMouse
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: jarvisBackend.setSector(modelData.id)
                                }
                            }
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: sectorInfoCol.implicitHeight + 28
                        radius: 12
                        color: window.isDark ? "#0A172B" : "#F8FAFC"
                        border.color: window.isDark ? "#183650" : "#E2E8F0"
                        Column {
                            id: sectorInfoCol
                            x: 14; y: 14
                            width: parent.width - 28
                            spacing: 8
                            Text {
                                width: parent.width
                                text: (jarvisBackend.sectorInfo.icon || "") + "  Setor ativo: " + (jarvisBackend.sectorInfo.name || "Geral")
                                color: textPrimary; font.pixelSize: 12; font.weight: Font.DemiBold
                            }
                            Text {
                                width: parent.width
                                text: jarvisBackend.sectorInfo.description || ""
                                color: textMuted; font.pixelSize: 9; wrapMode: Text.Wrap
                            }
                            Repeater {
                                model: jarvisBackend.sectorInfo.capabilities || []
                                delegate: Text {
                                    width: sectorInfoCol.width
                                    text: "• " + modelData
                                    color: window.isDark ? "#BFE9F5" : "#0F172A"
                                    font.pixelSize: 9
                                    wrapMode: Text.Wrap
                                }
                            }
                            Text {
                                width: parent.width
                                visible: (jarvisBackend.hiddenViews || []).length > 0
                                text: "Telas ocultas neste setor: " + (jarvisBackend.hiddenViews || []).join(", ").toUpperCase()
                                color: "#F6C453"; font.pixelSize: 8; wrapMode: Text.Wrap
                            }
                        }
                    }
                }
            }



            RowLayout {
                Layout.fillWidth: true
                Layout.preferredHeight: 50
                spacing: 12

                Text {
                    Layout.fillWidth: true
                    text: settingsDialog.tab === 2
                          ? "As chaves de API ficam cifradas — só saem daqui para o provedor que você escolher."
                          : ""
                    color: textMuted
                    font.pixelSize: 9
                    wrapMode: Text.Wrap
                }

                JarvisButton {
                    variant: "secondary"
                    width: 116; height: 42
                    text: "✕  CANCELAR"
                    onClicked: settingsDialog.close()
                }

                JarvisButton {
                    variant: "save"
                    width: 164; height: 42
                    text: "✔  SALVAR E APLICAR"
                    textSize: 10
                    onClicked: {
                        jarvisBackend.setSystemName(systemNameField.text.trim())
                        jarvisBackend.savePermissions(
                            permAgentEnabled.checked,
                            permFsRead.checked,
                            permFsWrite.checked,
                            permShell.checked,
                            permBrowser.checked,
                            permRootsArea.text,
                            permSsh.checked
                        )
                        jarvisBackend.saveVoiceInput(
                            wakeEnabledSwitch.checked,
                            wakePhraseField.text,
                            wakeRequiredSwitch.checked,
                            transcriptionEngineBox.currentText,
                            transcriptionBox.currentText,
                            voiceSilenceBox.currentText
                        )
                        jarvisBackend.saveWeatherCity(weatherCityField.text)
                        jarvisBackend.saveWebcam(webcamSwitch.checked, parseInt(webcamIndexField.text || "0"))
                        jarvisBackend.saveSettings(
                            aiProviderBox.currentText,
                            (aiModelBox.editText || aiModelBox.currentText).trim(),
                            voiceEngineBox.currentText,
                            voiceModelBox.currentText,
                            voiceNameBox.currentText,
                            conversationApiKeyField.text,
                            geminiVoiceApiKeyField.text
                        )
                        conversationApiKeyField.clear()
                        geminiVoiceApiKeyField.clear()
                        jarvisBackend.savePersona(
                            pName.text,
                            pPersonality.currentText,
                            pTone.currentText,
                            pAccent.currentText,
                            (jarvisBackend.assistantPersona.tts_voice || ""),
                            (jarvisBackend.assistantPersona.tts_rate || 185),
                            (jarvisBackend.assistantPersona.tts_volume !== undefined
                                ? jarvisBackend.assistantPersona.tts_volume : 1.0),
                            pCustom.text
                        )
                        var selected = providerBox.find(jarvisBackend.selectedAiProviderKey)
                        if (selected >= 0) providerBox.currentIndex = selected
                        settingsDialog.close()
                    }
                }
            }
        }
    }

    // ============================================================ MODAL QR CODE WHATSAPP
    Popup {
        id: whatsappQrModal
        objectName: "whatsappQrModal"
        parent: Overlay.overlay
        anchors.centerIn: parent
        width: Math.min(window.width - 160, 520)
        implicitHeight: qrModalCol.implicitHeight + 48
        modal: true
        focus: true
        padding: 0
        closePolicy: Popup.CloseOnEscape

        Overlay.modal: Rectangle { color: window.isDark ? "#DD020712" : "#80000000" }
        background: Rectangle {
            radius: 16
            color: window.isDark ? "#0B1526" : "#FFFFFF"
            border.color: window.isDark ? "#26516A" : "#CBD5E1"
            border.width: 1
        }

        contentItem: ColumnLayout {
            id: qrModalCol
            anchors.fill: parent
            anchors.margins: 24
            spacing: 16

            RowLayout {
                Layout.fillWidth: true
                spacing: 12
                Rectangle {
                    width: 40; height: 40; radius: 20
                    color: window.isDark ? "#0C2E20" : "#DCFCE7"
                    border.color: window.isDark ? "#1E824C" : "#86EFAC"
                    Text { anchors.centerIn: parent; text: "💬"; font.pixelSize: 18 }
                }
                Column {
                    Layout.fillWidth: true
                    spacing: 2
                    Text {
                        text: "CONEXÃO WHATSAPP // BAILEYS"
                        color: textPrimary
                        font.pixelSize: 14
                        font.weight: Font.DemiBold
                        font.letterSpacing: 1.3
                    }
                    Text {
                        text: "Escaneie o QR Code com o aplicativo WhatsApp no seu celular"
                        color: textMuted
                        font.pixelSize: 9
                    }
                }
                JarvisButton {
                    variant: "close"
                    width: 32; height: 32
                    text: "✕"
                    onClicked: whatsappQrModal.close()
                }
            }

            Rectangle { Layout.fillWidth: true; height: 1; color: window.isDark ? "#142840" : "#E2E8F0" }

            // Se Conectado com sucesso
            ColumnLayout {
                visible: jarvisBackend.whatsappConnected
                Layout.fillWidth: true
                spacing: 12
                Layout.alignment: Qt.AlignHCenter

                Rectangle {
                    width: 60; height: 60; radius: 30
                    color: window.isDark ? "#0C2E20" : "#DCFCE7"
                    Layout.alignment: Qt.AlignHCenter
                    Text { anchors.centerIn: parent; text: "✔"; color: green; font.pixelSize: 26; font.weight: Font.Bold }
                }
                Text {
                    text: "WhatsApp Conectado com Sucesso!"
                    color: textPrimary
                    font.pixelSize: 13
                    font.weight: Font.DemiBold
                    Layout.alignment: Qt.AlignHCenter
                }
                Text {
                    text: "Número: +" + jarvisBackend.whatsappUserPhone + " (" + (jarvisBackend.whatsappUserName || "Dispositivo") + ")"
                    color: green
                    font.pixelSize: 10
                    Layout.alignment: Qt.AlignHCenter
                }
                JarvisButton {
                    variant: "success"
                    text: "CONCLUÍDO"
                    Layout.alignment: Qt.AlignHCenter
                    implicitHeight: 36
                    onClicked: whatsappQrModal.close()
                }
            }

            // Se Desconectado / Gerando QR
            ColumnLayout {
                visible: !jarvisBackend.whatsappConnected
                Layout.fillWidth: true
                spacing: 14
                Layout.alignment: Qt.AlignHCenter

                Rectangle {
                    Layout.preferredWidth: 240
                    Layout.preferredHeight: 240
                    Layout.alignment: Qt.AlignHCenter
                    radius: 12
                    color: "white"
                    border.color: cyan
                    border.width: 2

                    Image {
                        anchors.fill: parent
                        anchors.margins: 10
                        fillMode: Image.PreserveAspectFit
                        source: jarvisBackend.whatsappQrCode
                        visible: jarvisBackend.whatsappQrCode !== ""
                    }

                    Column {
                        anchors.centerIn: parent
                        visible: jarvisBackend.whatsappQrCode === ""
                        spacing: 8
                        Text { anchors.horizontalCenter: parent.horizontalCenter; text: "⌛"; font.pixelSize: 28 }
                        Text {
                            anchors.horizontalCenter: parent.horizontalCenter
                            text: "Gerando QR Code..."
                            color: "#0369A1"
                            font.pixelSize: 10
                            font.weight: Font.DemiBold
                        }
                    }
                }

                Column {
                    Layout.fillWidth: true
                    spacing: 4
                    Text { text: "1. Abra o WhatsApp no celular > Aparelhos conectados"; color: textPrimary; font.pixelSize: 10 }
                    Text { text: "2. Toque em Conectar um aparelho"; color: textPrimary; font.pixelSize: 10 }
                    Text { text: "3. Aponte a câmera para o QR Code acima"; color: textPrimary; font.pixelSize: 10 }
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 10
                    JarvisButton {
                        variant: "secondary"
                        text: "🔄  Gerar novo QR"
                        Layout.fillWidth: true
                        implicitHeight: 36
                        onClicked: jarvisBackend.connectWhatsApp()
                    }
                    JarvisButton {
                        variant: "close"
                        text: "✕  Cancelar"
                        Layout.fillWidth: true
                        implicitHeight: 36
                        onClicked: whatsappQrModal.close()
                    }
                }
            }
        }
    }

    // ============================================================ MODAL CONFIGURAR MODELO DE IA
    Popup {
        id: agentEditorModal
        objectName: "agentEditorModal"
        parent: Overlay.overlay
        anchors.centerIn: parent
        width: Math.min(window.width - 120, 640)
        implicitHeight: modalCol.implicitHeight + 44
        modal: true
        focus: true
        padding: 0
        closePolicy: Popup.CloseOnEscape

        property int editingId: 0
        property string testStatusText: ""
        property bool testStatusSuccess: false
        property bool isTesting: false

        readonly property bool isFreeTextProvider: {
            var p = (agentProviderBox.currentText || "").toLowerCase().trim()
            return p === "lm studio" || p === "ollama" || p === "openrouter"
        }

        Connections {
            target: jarvisBackend
            function onAiAgentTestResult(success, message) {
                agentEditorModal.isTesting = false
                agentEditorModal.testStatusSuccess = success
                agentEditorModal.testStatusText = message
            }
        }

        function openNew() {
            editingId = 0
            var pIdx = agentProviderBox.find("OpenAI")
            if (pIdx >= 0) agentProviderBox.currentIndex = pIdx
            agentModelBox.model = jarvisBackend.aiAgentModels("OpenAI")
            agentModelBox.currentIndex = 0 // gpt-4.5-preview
            agentModelField.text = ""
            agentApiKeyField.text = ""
            agentBaseUrlField.text = ""
            testStatusText = ""
            isTesting = false
            agentEditorModal.open()
        }

        function openEdit(agent) {
            editingId = agent.id || 0
            var prov = agent.provider || "OpenAI"
            var pIdx = agentProviderBox.find(prov)
            if (pIdx >= 0) {
                agentProviderBox.currentIndex = pIdx
            }
            if (agentEditorModal.isFreeTextProvider) {
                agentModelField.text = agent.model || ""
            } else {
                agentModelBox.model = jarvisBackend.aiAgentModels(prov)
                var mIdx = agentModelBox.find(agent.model || "")
                if (mIdx >= 0) {
                    agentModelBox.currentIndex = mIdx
                } else {
                    agentModelBox.currentIndex = 0
                }
            }
            agentApiKeyField.text = agent.api_key || ""
            agentBaseUrlField.text = agent.base_url || ""
            testStatusText = ""
            isTesting = false
            agentEditorModal.open()
        }

        Overlay.modal: Rectangle { color: window.isDark ? "#DD020712" : "#80000000" }
        background: Rectangle {
            radius: 16
            color: window.isDark ? "#0B1526" : "#FFFFFF"
            border.color: window.isDark ? "#26516A" : "#CBD5E1"
            border.width: 1
        }

        contentItem: ColumnLayout {
            id: modalCol
            anchors.fill: parent
            anchors.margins: 22
            spacing: 16

            // Header do Modal
            RowLayout {
                Layout.fillWidth: true
                spacing: 12
                Rectangle {
                    width: 38; height: 38; radius: 19
                    color: window.isDark ? "#123049" : "#E0F2FE"
                    border.color: cyan
                    Text { anchors.centerIn: parent; text: "🤖"; font.pixelSize: 18 }
                }
                Column {
                    Layout.fillWidth: true
                    spacing: 2
                    Text {
                        text: "CONFIGURAR MODELO DE IA"
                        color: textPrimary
                        font.pixelSize: 15
                        font.weight: Font.DemiBold
                        font.letterSpacing: 1.3
                    }
                    Text {
                        text: "Selecione o provedor, defina o modelo de linguagem, chave de API e teste a conexão"
                        color: textMuted
                        font.pixelSize: 9
                    }
                }
                JarvisButton {
                    variant: "close"
                    width: 32; height: 32
                    text: "✕"
                    onClicked: agentEditorModal.close()
                }
            }

            Rectangle { Layout.fillWidth: true; height: 1; color: window.isDark ? "#142840" : "#E2E8F0" }

            // Card Principal de Configuração do Modelo
            Rectangle {
                Layout.fillWidth: true
                implicitHeight: formCol.implicitHeight + 28
                radius: 12
                color: window.isDark ? "#081324" : "#F8FAFC"
                border.color: window.isDark ? "#152A42" : "#E2E8F0"

                ColumnLayout {
                    id: formCol
                    anchors.fill: parent
                    anchors.margins: 16
                    spacing: 14

                    // Linha Provedor e Modelo
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 14

                        // Provedor
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 5
                            Text { text: "PROVEDOR DE IA"; color: textMuted; font.pixelSize: 8; font.letterSpacing: 1 }
                            ComboBox {
                                id: agentProviderBox
                                Layout.fillWidth: true
                                Layout.preferredHeight: 40
                                model: ["OpenAI", "Anthropic", "Gemini", "Groq", "OpenRouter", "LM Studio", "Ollama"]
                                font.pixelSize: 11

                                delegate: ItemDelegate {
                                    width: agentProviderBox.width
                                    height: 38
                                    highlighted: agentProviderBox.highlightedIndex === index
                                    contentItem: Text {
                                        text: modelData
                                        color: window.isDark ? "#EAFBFF" : "#0F172A"
                                        font.pixelSize: 11
                                        verticalAlignment: Text.AlignVCenter
                                        elide: Text.ElideRight
                                    }
                                    background: Rectangle {
                                        color: parent.highlighted ? (window.isDark ? "#14364C" : "#E0F2FE") : (window.isDark ? "#0A152A" : "#FFFFFF")
                                    }
                                }

                                contentItem: Text {
                                    leftPadding: 12
                                    rightPadding: 28
                                    text: agentProviderBox.displayText
                                    color: textPrimary
                                    font.pixelSize: 11
                                    verticalAlignment: Text.AlignVCenter
                                    elide: Text.ElideRight
                                }

                                background: Rectangle {
                                    radius: 8
                                    color: window.isDark ? "#0D1D33" : "#FFFFFF"
                                    border.color: agentProviderBox.activeFocus || agentProviderBox.popup.visible ? cyan : (window.isDark ? "#23435E" : "#CBD5E1")
                                }

                                popup: Popup {
                                    y: agentProviderBox.height + 4
                                    width: agentProviderBox.width
                                    implicitHeight: Math.min(contentItem.implicitHeight + 4, 260)
                                    padding: 2
                                    contentItem: ListView {
                                        clip: true
                                        implicitHeight: contentHeight
                                        model: agentProviderBox.popup.visible ? agentProviderBox.delegateModel : null
                                        currentIndex: agentProviderBox.highlightedIndex
                                        ScrollIndicator.vertical: ScrollIndicator {}
                                    }
                                    background: Rectangle {
                                        radius: 8
                                        color: window.isDark ? "#0A152A" : "#FFFFFF"
                                        border.color: window.isDark ? "#23435E" : "#CBD5E1"
                                        border.width: 1
                                    }
                                }

                                onActivated: {
                                    agentEditorModal.testStatusText = ""
                                    if (!agentEditorModal.isFreeTextProvider) {
                                        agentModelBox.model = jarvisBackend.aiAgentModels(currentText)
                                        agentModelBox.currentIndex = 0
                                    } else {
                                        agentModelField.text = ""
                                    }
                                }
                            }
                        }

                        // Modelo de Linguagem (LLM)
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 5

                            RowLayout {
                                Layout.fillWidth: true
                                Text { text: "MODELO DE LINGUAGEM (LLM)"; color: textMuted; font.pixelSize: 8; font.letterSpacing: 1 }
                                Item { Layout.fillWidth: true }
                                Text {
                                    visible: agentEditorModal.isFreeTextProvider
                                    text: "Livre para digitar"
                                    color: cyan
                                    font.pixelSize: 8
                                    font.weight: Font.DemiBold
                                }
                            }

                            // Dropdown para OpenAI, Anthropic, Gemini, Groq
                            ComboBox {
                                id: agentModelBox
                                Layout.fillWidth: true
                                Layout.preferredHeight: 40
                                visible: !agentEditorModal.isFreeTextProvider
                                model: jarvisBackend.aiAgentModels(agentProviderBox.currentText)
                                font.pixelSize: 11

                                delegate: ItemDelegate {
                                    width: agentModelBox.width
                                    height: 38
                                    highlighted: agentModelBox.highlightedIndex === index
                                    contentItem: Text {
                                        text: modelData
                                        color: window.isDark ? "#EAFBFF" : "#0F172A"
                                        font.pixelSize: 11
                                        verticalAlignment: Text.AlignVCenter
                                        elide: Text.ElideRight
                                    }
                                    background: Rectangle {
                                        color: parent.highlighted ? (window.isDark ? "#14364C" : "#E0F2FE") : (window.isDark ? "#0A152A" : "#FFFFFF")
                                    }
                                }

                                contentItem: Text {
                                    leftPadding: 12
                                    rightPadding: 28
                                    text: agentModelBox.displayText
                                    color: textPrimary
                                    font.pixelSize: 11
                                    verticalAlignment: Text.AlignVCenter
                                    elide: Text.ElideRight
                                }

                                background: Rectangle {
                                    radius: 8
                                    color: window.isDark ? "#0D1D33" : "#FFFFFF"
                                    border.color: agentModelBox.activeFocus || agentModelBox.popup.visible ? cyan : (window.isDark ? "#23435E" : "#CBD5E1")
                                }

                                popup: Popup {
                                    y: agentModelBox.height + 4
                                    width: agentModelBox.width
                                    implicitHeight: Math.min(contentItem.implicitHeight + 4, 260)
                                    padding: 2
                                    contentItem: ListView {
                                        clip: true
                                        implicitHeight: contentHeight
                                        model: agentModelBox.popup.visible ? agentModelBox.delegateModel : null
                                        currentIndex: agentModelBox.highlightedIndex
                                        ScrollIndicator.vertical: ScrollIndicator {}
                                    }
                                    background: Rectangle {
                                        radius: 8
                                        color: window.isDark ? "#0A152A" : "#FFFFFF"
                                        border.color: window.isDark ? "#23435E" : "#CBD5E1"
                                        border.width: 1
                                    }
                                }
                            }

                            // Campo Livre para LM Studio, Ollama, OpenRouter
                            TextField {
                                id: agentModelField
                                Layout.fillWidth: true
                                Layout.preferredHeight: 40
                                visible: agentEditorModal.isFreeTextProvider
                                placeholderText: agentProviderBox.currentText === "OpenRouter" ? "Ex.: openai/gpt-4o, deepseek/deepseek-r1"
                                                : (agentProviderBox.currentText === "LM Studio" ? "Ex.: local-model, mistral-7b-instruct"
                                                : "Ex.: llama3.2, deepseek-r1:8b, qwen2.5-coder")
                                placeholderTextColor: window.isDark ? "#526D83" : "#94A3B8"
                                color: textPrimary
                                font.pixelSize: 11
                                leftPadding: 12
                                background: Rectangle {
                                    radius: 8
                                    color: window.isDark ? "#0D1D33" : "#FFFFFF"
                                    border.color: parent.activeFocus ? cyan : (window.isDark ? "#23435E" : "#CBD5E1")
                                }
                            }
                        }
                    }

                    // Chave de API e Botão Testar Conexão
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 5

                        RowLayout {
                            Layout.fillWidth: true
                            Text {
                                text: (agentProviderBox.currentText === "LM Studio" || agentProviderBox.currentText === "Ollama") ? "CHAVE DE API (OPCIONAL PARA LOCAL)" : "CHAVE DE API (API KEY)";
                                color: textMuted
                                font.pixelSize: 8
                                font.letterSpacing: 1
                            }
                            Item { Layout.fillWidth: true }
                            Text {
                                text: agentShowKeyBtn.checked ? "👁  Ocultar chave" : "👁  Mostrar chave"
                                color: cyan
                                font.pixelSize: 8
                                MouseArea {
                                    anchors.fill: parent
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: agentShowKeyBtn.checked = !agentShowKeyBtn.checked
                                }
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10

                            TextField {
                                id: agentApiKeyField
                                Layout.fillWidth: true
                                Layout.preferredHeight: 38
                                echoMode: agentShowKeyBtn.checked ? TextInput.Normal : TextInput.Password
                                passwordCharacter: "*"
                                placeholderText: (agentProviderBox.currentText === "LM Studio" || agentProviderBox.currentText === "Ollama") ? "Opcional para conexões locais" : "Cole a API Key aqui (ex.: sk-..., AIzaSy..., etc.)"
                                placeholderTextColor: window.isDark ? "#526D83" : "#94A3B8"
                                color: textPrimary
                                font.pixelSize: 11
                                leftPadding: 12
                                background: Rectangle {
                                    radius: 8
                                    color: window.isDark ? "#0D1D33" : "#FFFFFF"
                                    border.color: parent.activeFocus ? cyan : (window.isDark ? "#23435E" : "#CBD5E1")
                                }
                            }

                            Button {
                                id: agentShowKeyBtn
                                checkable: true
                                visible: false
                            }

                            JarvisButton {
                                variant: "save"
                                text: agentEditorModal.isTesting ? "⏳  TESTANDO..." : "⚡  TESTAR CONEXÃO"
                                implicitHeight: 38
                                leftPadding: 14; rightPadding: 14
                                textSize: 9
                                enabled: !agentEditorModal.isTesting
                                onClicked: {
                                    var currentModel = agentEditorModal.isFreeTextProvider ? agentModelField.text.trim() : (agentModelBox.currentText || "")
                                    agentEditorModal.isTesting = true
                                    agentEditorModal.testStatusText = "Testando conexão com " + agentProviderBox.currentText + "..."
                                    jarvisBackend.testAiModelConnection(
                                        agentProviderBox.currentText,
                                        currentModel,
                                        agentApiKeyField.text.trim(),
                                        agentBaseUrlField.text.trim()
                                    )
                                }
                            }
                        }
                    }

                    // Banner de Resultado do Teste
                    Rectangle {
                        visible: agentEditorModal.testStatusText !== ""
                        Layout.fillWidth: true
                        implicitHeight: 36
                        radius: 8
                        color: agentEditorModal.testStatusSuccess ? (window.isDark ? "#0C2E20" : "#DCFCE7") : (window.isDark ? "#2A1820" : "#FEE2E2")
                        border.color: agentEditorModal.testStatusSuccess ? (window.isDark ? "#1E824C" : "#86EFAC") : "#EF4444"

                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: 12
                            anchors.rightMargin: 12
                            spacing: 8

                            Text {
                                text: agentEditorModal.testStatusSuccess ? "✔" : "⚠️"
                                color: agentEditorModal.testStatusSuccess ? green : "#EF4444"
                                font.pixelSize: 12
                                font.weight: Font.Bold
                            }
                            Text {
                                text: agentEditorModal.testStatusText
                                color: textPrimary
                                font.pixelSize: 10
                                font.weight: Font.Medium
                                Layout.fillWidth: true
                                elide: Text.ElideRight
                            }
                        }
                    }

                    // Base URL Customizada
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 5
                        RowLayout {
                            Layout.fillWidth: true
                            Text { text: "ENDPOINT / BASE URL (OPCIONAL)"; color: textMuted; font.pixelSize: 8; font.letterSpacing: 1 }
                            Item { Layout.fillWidth: true }
                            Text {
                                text: agentProviderBox.currentText === "LM Studio" ? "Padrão: http://localhost:1234/v1" : (agentProviderBox.currentText === "Ollama" ? "Padrão: http://localhost:11434/v1" : (agentProviderBox.currentText === "OpenRouter" ? "https://openrouter.ai/api/v1" : "Deixe vazio para URL oficial"))
                                color: textMuted
                                font.pixelSize: 8
                            }
                        }
                        TextField {
                            id: agentBaseUrlField
                            Layout.fillWidth: true
                            Layout.preferredHeight: 38
                            placeholderText: agentProviderBox.currentText === "LM Studio" ? "http://localhost:1234/v1" : (agentProviderBox.currentText === "Ollama" ? "http://localhost:11434/v1" : (agentProviderBox.currentText === "OpenRouter" ? "https://openrouter.ai/api/v1" : "https://api.openai.com/v1"))
                            placeholderTextColor: window.isDark ? "#526D83" : "#94A3B8"
                            color: textPrimary
                            font.pixelSize: 11
                            leftPadding: 12
                            background: Rectangle {
                                radius: 8
                                color: window.isDark ? "#0D1D33" : "#FFFFFF"
                                border.color: parent.activeFocus ? cyan : (window.isDark ? "#23435E" : "#CBD5E1")
                            }
                        }
                    }
                }
            }

            Rectangle { Layout.fillWidth: true; height: 1; color: window.isDark ? "#142840" : "#E2E8F0" }

            // Footer do Modal
            RowLayout {
                Layout.fillWidth: true
                spacing: 12

                JarvisButton {
                    variant: "secondary"
                    text: "✕  CANCELAR"
                    implicitHeight: 40
                    implicitWidth: 120
                    onClicked: agentEditorModal.close()
                }

                Item { Layout.fillWidth: true }

                JarvisButton {
                    variant: "save"
                    text: "✔  SALVAR CONFIGURAÇÃO"
                    implicitHeight: 40
                    leftPadding: 24; rightPadding: 24
                    onClicked: {
                        var chosenModel = agentEditorModal.isFreeTextProvider ? agentModelField.text.trim() : (agentModelBox.currentText || "")
                        if (!chosenModel) {
                            chosenModel = "default"
                        }
                        var agentName = "Modelo " + agentProviderBox.currentText
                        jarvisBackend.saveAiAgent(
                            agentEditorModal.editingId,
                            agentName,
                            agentProviderBox.currentText,
                            chosenModel,
                            agentApiKeyField.text.trim(),
                            agentBaseUrlField.text.trim(),
                            "",
                            0.7,
                            true
                        )
                        agentEditorModal.close()
                    }
                }
            }
        }
    }

    // ============================================================ MODAL CRIAR / EDITAR AGENTE DE ATENDIMENTO
    Popup {
        id: communicationAgentModal
        objectName: "communicationAgentModal"
        parent: Overlay.overlay
        anchors.centerIn: parent
        width: Math.min(window.width - 80, 1020)
        height: Math.min(window.height - 40, 680)
        modal: true
        focus: true
        padding: 0
        closePolicy: Popup.CloseOnEscape

        property int editingId: 0
        property int currentNavTab: 0
        property string selectedEmojiLevel: "Normal"
        property var responsibilitiesList: ["Atender clientes via WhatsApp", "Esclarecer dúvidas sobre produtos e serviços"]

        function getAiModelsDisplayList() {
            var list = []
            var agents = jarvisBackend.aiAgents || []
            if (agents.length === 0) {
                list.push("Nenhum Modelo de IA configurado")
            } else {
                for (var i = 0; i < agents.length; i++) {
                    var ag = agents[i]
                    var name = ag.name || ("Modelo " + (ag.provider || "IA"))
                    var prov = ag.provider || "OpenAI"
                    var mod = ag.model || ""
                    list.push("[" + prov + "] " + name + " (" + mod + ")")
                }
            }
            return list
        }

        function findModelIndex(modelId) {
            var agents = jarvisBackend.aiAgents || []
            for (var i = 0; i < agents.length; i++) {
                if (agents[i].id === modelId) return i
            }
            return 0
        }

        function openNew() {
            editingId = 0
            currentNavTab = 0
            caNameField.text = ""
            caAgeField.text = ""
            caGenderBox.currentIndex = 0
            caRoleField.text = ""
            caModelBox.model = getAiModelsDisplayList()
            caModelBox.currentIndex = 0
            caToneBox.currentIndex = 0
            caFormalityBox.currentIndex = 0
            selectedEmojiLevel = "Normal"
            caResponseStyleBox.currentIndex = 0
            caLanguageBox.currentIndex = 0
            caJobDescArea.text = ""
            responsibilitiesList = ["Atender clientes via WhatsApp", "Esclarecer dúvidas sobre produtos e serviços"]
            caCompanyNameField.text = ""
            caCompanySegmentField.text = ""
            caCompanyDescArea.text = ""
            caCompanyProductsArea.text = ""
            caCompanyAudienceField.text = ""
            caCompanyRegionsField.text = ""
            caCompanyHoursField.text = ""
            caCompanyPaymentField.text = ""
            caCompanyPoliciesArea.text = ""
            caActiveSwitch.checked = true
            communicationAgentModal.open()
        }

        function openEdit(agent) {
            editingId = agent.id || 0
            currentNavTab = 0
            caNameField.text = agent.name || ""
            caAgeField.text = agent.age || ""
            var gIdx = caGenderBox.find(agent.gender || "")
            caGenderBox.currentIndex = gIdx >= 0 ? gIdx : 0
            caRoleField.text = agent.role || ""
            caModelBox.model = getAiModelsDisplayList()
            var mIdx = findModelIndex(agent.model_id)
            caModelBox.currentIndex = mIdx >= 0 ? mIdx : 0
            var tIdx = caToneBox.find(agent.tone || "")
            caToneBox.currentIndex = tIdx >= 0 ? tIdx : 0
            var fIdx = caFormalityBox.find(agent.formality || "")
            caFormalityBox.currentIndex = fIdx >= 0 ? fIdx : 0
            selectedEmojiLevel = agent.emoji_level || "Normal"
            var rIdx = caResponseStyleBox.find(agent.response_style || "")
            caResponseStyleBox.currentIndex = rIdx >= 0 ? rIdx : 0
            var lIdx = caLanguageBox.find(agent.language || "Português (Brasil)")
            caLanguageBox.currentIndex = lIdx >= 0 ? lIdx : 0
            caJobDescArea.text = agent.job_description || ""
            try {
                responsibilitiesList = JSON.parse(agent.responsibilities || "[]")
                if (!Array.isArray(responsibilitiesList) || responsibilitiesList.length === 0) {
                    responsibilitiesList = ["Atender clientes via WhatsApp", "Esclarecer dúvidas sobre produtos e serviços"]
                }
            } catch (e) {
                responsibilitiesList = ["Atender clientes via WhatsApp", "Esclarecer dúvidas sobre produtos e serviços"]
            }
            caCompanyNameField.text = agent.company_name || ""
            caCompanySegmentField.text = agent.company_segment || ""
            caCompanyDescArea.text = agent.company_description || agent.company_info || ""
            caCompanyProductsArea.text = agent.company_products || ""
            caCompanyAudienceField.text = agent.company_target_audience || ""
            caCompanyRegionsField.text = agent.company_regions || ""
            caCompanyHoursField.text = agent.company_business_hours || ""
            caCompanyPaymentField.text = agent.company_payment_methods || ""
            caCompanyPoliciesArea.text = agent.company_policies || ""
            caActiveSwitch.checked = (agent.active !== 0)
            communicationAgentModal.open()
        }

        Overlay.modal: Rectangle { color: window.isDark ? "#DD020712" : "#80000000" }
        background: Rectangle {
            radius: 16
            color: window.isDark ? "#0B1526" : "#FFFFFF"
            border.color: window.isDark ? "#26516A" : "#CBD5E1"
            border.width: 1
        }

        contentItem: ColumnLayout {
            anchors.fill: parent
            anchors.margins: 22
            spacing: 16

            // Header do Modal
            RowLayout {
                Layout.fillWidth: true
                spacing: 12
                Rectangle {
                    width: 38; height: 38; radius: 19
                    color: window.isDark ? "#0E2822" : "#DCFCE7"
                    border.color: green
                    Text { anchors.centerIn: parent; text: "🤖"; font.pixelSize: 18 }
                }
                Column {
                    Layout.fillWidth: true
                    spacing: 2
                    Text {
                        text: communicationAgentModal.editingId > 0 ? "EDITAR AGENTE DE IA" : "CRIAR AGENTE DE IA"
                        color: textPrimary
                        font.pixelSize: 15
                        font.weight: Font.DemiBold
                        font.letterSpacing: 1.3
                    }
                    Text {
                        text: "Defina perfil, personalidade, função e empresa para o atendimento via WhatsApp"
                        color: textMuted
                        font.pixelSize: 9
                    }
                }
                Row {
                    spacing: 8
                    Layout.alignment: Qt.AlignVCenter
                    Text {
                        anchors.verticalCenter: parent.verticalCenter
                        text: "STATUS:"
                        color: textMuted
                        font.pixelSize: 8
                        font.letterSpacing: 1
                    }
                    Switch {
                        id: caActiveSwitch
                        checked: true
                    }
                    Text {
                        anchors.verticalCenter: parent.verticalCenter
                        text: caActiveSwitch.checked ? "ATIVO" : "INATIVO"
                        color: caActiveSwitch.checked ? green : textMuted
                        font.pixelSize: 9
                        font.weight: Font.Bold
                    }
                }
                JarvisButton {
                    variant: "close"
                    width: 32; height: 32
                    text: "✕"
                    onClicked: communicationAgentModal.close()
                }
            }

            Rectangle { Layout.fillWidth: true; height: 1; color: window.isDark ? "#142840" : "#E2E8F0" }

            // Corpo Principal com Navegação Lateral e Conteúdo
            RowLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: 20

                // ------------------------------------ Menu Lateral de Abas
                Rectangle {
                    Layout.preferredWidth: 230
                    Layout.fillHeight: true
                    radius: 12
                    color: window.isDark ? "#070E1B" : "#F8FAFC"
                    border.color: window.isDark ? "#142840" : "#E2E8F0"

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 12
                        spacing: 8

                        Repeater {
                            model: [
                                {"idx": 0, "name": "1. Perfil da IA", "icon": "👤"},
                                {"idx": 1, "name": "2. Personalidade da IA", "icon": "✨"},
                                {"idx": 2, "name": "3. Função da IA na empresa", "icon": "🤖"},
                                {"idx": 3, "name": "4. Sobre a empresa", "icon": "🏢"}
                            ]

                            delegate: Rectangle {
                                Layout.fillWidth: true
                                Layout.preferredHeight: 44
                                radius: 10
                                property bool active: communicationAgentModal.currentNavTab === modelData.idx
                                color: active ? (window.isDark ? "#0E2B22" : "#E6F7F2") : (navMouse.containsMouse ? (window.isDark ? "#0D1E32" : "#EDF2F7") : "transparent")
                                border.color: active ? (window.isDark ? "#1E824C" : "#A3E6CD") : "transparent"
                                border.width: 1

                                RowLayout {
                                    anchors.fill: parent
                                    anchors.leftMargin: 14
                                    anchors.rightMargin: 14
                                    spacing: 12

                                    Text {
                                        text: modelData.icon
                                        font.pixelSize: 14
                                    }

                                    Text {
                                        text: modelData.name
                                        color: parent.parent.active ? (window.isDark ? "#4EF2A6" : "#00875A") : textPrimary
                                        font.pixelSize: 11
                                        font.weight: parent.parent.active ? Font.DemiBold : Font.Normal
                                        Layout.fillWidth: true
                                    }
                                }

                                MouseArea {
                                    id: navMouse
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: communicationAgentModal.currentNavTab = modelData.idx
                                }
                            }
                        }

                        Item { Layout.fillHeight: true }
                    }
                }

                // ------------------------------------ Painel de Conteúdo das Abas
                ScrollView {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    contentWidth: availableWidth
                    clip: true

                    ColumnLayout {
                        width: parent.width
                        spacing: 16

                        // =================================== ABA 0: 1. Perfil da IA
                        ColumnLayout {
                            visible: communicationAgentModal.currentNavTab === 0
                            Layout.fillWidth: true
                            spacing: 16

                            // Linha 1: Nome da IA e Idade da IA
                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 16

                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 4

                                    Text { text: "Nome da IA *"; color: textPrimary; font.pixelSize: 11; font.weight: Font.DemiBold }
                                    TextField {
                                        id: caNameField
                                        Layout.fillWidth: true
                                        Layout.preferredHeight: 40
                                        placeholderText: "Ex.: Ana Assistente"
                                        placeholderTextColor: window.isDark ? "#526D83" : "#94A3B8"
                                        color: textPrimary
                                        font.pixelSize: 11
                                        leftPadding: 12
                                        background: Rectangle {
                                            radius: 8
                                            color: window.isDark ? "#0D1D33" : "#FFFFFF"
                                            border.color: parent.activeFocus ? green : (window.isDark ? "#23435E" : "#CBD5E1")
                                        }
                                    }
                                    Text { text: "Este será o nome com que as pessoas falarão com a IA."; color: textMuted; font.pixelSize: 9 }
                                }

                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 4

                                    Text { text: "Idade da IA"; color: textPrimary; font.pixelSize: 11; font.weight: Font.DemiBold }
                                    TextField {
                                        id: caAgeField
                                        Layout.fillWidth: true
                                        Layout.preferredHeight: 40
                                        placeholderText: "Ex.: 28"
                                        placeholderTextColor: window.isDark ? "#526D83" : "#94A3B8"
                                        color: textPrimary
                                        font.pixelSize: 11
                                        leftPadding: 12
                                        background: Rectangle {
                                            radius: 8
                                            color: window.isDark ? "#0D1D33" : "#FFFFFF"
                                            border.color: parent.activeFocus ? green : (window.isDark ? "#23435E" : "#CBD5E1")
                                        }
                                    }
                                    Text { text: "Opcional. Define uma idade aparente para o perfil da IA."; color: textMuted; font.pixelSize: 9 }
                                }
                            }

                            // Linha 2: Gênero e Cargo/Função
                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 16

                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 4

                                    Text { text: "Gênero"; color: textPrimary; font.pixelSize: 11; font.weight: Font.DemiBold }
                                    ComboBox {
                                        id: caGenderBox
                                        Layout.fillWidth: true
                                        Layout.preferredHeight: 40
                                        model: ["Selecione o gênero", "Feminino", "Masculino", "Neutro", "Não especificado"]
                                        font.pixelSize: 11

                                        delegate: ItemDelegate {
                                            width: caGenderBox.width; height: 36
                                            highlighted: caGenderBox.highlightedIndex === index
                                            contentItem: Text { text: modelData; color: window.isDark ? "#EAFBFF" : "#0F172A"; font.pixelSize: 11; verticalAlignment: Text.AlignVCenter }
                                            background: Rectangle { color: parent.highlighted ? (window.isDark ? "#14364C" : "#E0F2FE") : (window.isDark ? "#0A152A" : "#FFFFFF") }
                                        }
                                        contentItem: Text { leftPadding: 12; rightPadding: 28; text: caGenderBox.displayText; color: textPrimary; font.pixelSize: 11; verticalAlignment: Text.AlignVCenter }
                                        background: Rectangle { radius: 8; color: window.isDark ? "#0D1D33" : "#FFFFFF"; border.color: caGenderBox.activeFocus || caGenderBox.popup.visible ? green : (window.isDark ? "#23435E" : "#CBD5E1") }
                                        popup: Popup {
                                            y: caGenderBox.height + 4; width: caGenderBox.width; implicitHeight: Math.min(contentItem.implicitHeight + 4, 220); padding: 2
                                            contentItem: ListView { clip: true; implicitHeight: contentHeight; model: caGenderBox.popup.visible ? caGenderBox.delegateModel : null; currentIndex: caGenderBox.highlightedIndex; ScrollIndicator.vertical: ScrollIndicator {} }
                                            background: Rectangle { radius: 8; color: window.isDark ? "#0A152A" : "#FFFFFF"; border.color: window.isDark ? "#23435E" : "#CBD5E1"; border.width: 1 }
                                        }
                                    }
                                    Text { text: "Define como o agente se apresenta durante a conversa."; color: textMuted; font.pixelSize: 9 }
                                }

                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 4

                                    Text { text: "Cargo/Função *"; color: textPrimary; font.pixelSize: 11; font.weight: Font.DemiBold }
                                    TextField {
                                        id: caRoleField
                                        Layout.fillWidth: true
                                        Layout.preferredHeight: 40
                                        placeholderText: "Ex.: Consultora de vendas"
                                        placeholderTextColor: window.isDark ? "#526D83" : "#94A3B8"
                                        color: textPrimary
                                        font.pixelSize: 11
                                        leftPadding: 12
                                        background: Rectangle {
                                            radius: 8
                                            color: window.isDark ? "#0D1D33" : "#FFFFFF"
                                            border.color: parent.activeFocus ? green : (window.isDark ? "#23435E" : "#CBD5E1")
                                        }
                                    }
                                    Text { text: "Informe qual é o cargo ou a função da IA na empresa."; color: textMuted; font.pixelSize: 9 }
                                }
                            }

                            // Linha 3: Modelo de IA (Seleciona da aba Agente de IA)
                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 4

                                Text { text: "Modelo de IA"; color: textPrimary; font.pixelSize: 11; font.weight: Font.DemiBold }
                                ComboBox {
                                    id: caModelBox
                                    Layout.fillWidth: true
                                    Layout.preferredHeight: 40
                                    model: communicationAgentModal.getAiModelsDisplayList()
                                    font.pixelSize: 11

                                    delegate: ItemDelegate {
                                        width: caModelBox.width; height: 38
                                        highlighted: caModelBox.highlightedIndex === index
                                        contentItem: Text { text: modelData; color: window.isDark ? "#EAFBFF" : "#0F172A"; font.pixelSize: 11; verticalAlignment: Text.AlignVCenter; elide: Text.ElideRight }
                                        background: Rectangle { color: parent.highlighted ? (window.isDark ? "#14364C" : "#E0F2FE") : (window.isDark ? "#0A152A" : "#FFFFFF") }
                                    }
                                    contentItem: Text { leftPadding: 12; rightPadding: 28; text: caModelBox.displayText; color: textPrimary; font.pixelSize: 11; verticalAlignment: Text.AlignVCenter; elide: Text.ElideRight }
                                    background: Rectangle { radius: 8; color: window.isDark ? "#0D1D33" : "#FFFFFF"; border.color: caModelBox.activeFocus || caModelBox.popup.visible ? green : (window.isDark ? "#23435E" : "#CBD5E1") }
                                    popup: Popup {
                                        y: caModelBox.height + 4; width: caModelBox.width; implicitHeight: Math.min(contentItem.implicitHeight + 4, 260); padding: 2
                                        contentItem: ListView { clip: true; implicitHeight: contentHeight; model: caModelBox.popup.visible ? caModelBox.delegateModel : null; currentIndex: caModelBox.highlightedIndex; ScrollIndicator.vertical: ScrollIndicator {} }
                                        background: Rectangle { radius: 8; color: window.isDark ? "#0A152A" : "#FFFFFF"; border.color: window.isDark ? "#23435E" : "#CBD5E1"; border.width: 1 }
                                    }
                                }
                                Text {
                                    text: (!jarvisBackend.aiAgents || jarvisBackend.aiAgents.length === 0)
                                          ? "⚠️ Nenhum modelo de IA configurado na aba 'Agente de IA'. Você pode salvar o agente agora e configurar o modelo a qualquer momento."
                                          : "Inteligência Artificial que processará e gerará as respostas deste agente.";
                                    color: (!jarvisBackend.aiAgents || jarvisBackend.aiAgents.length === 0) ? "#F6C453" : textMuted
                                    font.pixelSize: 9
                                }
                            }
                        }

                        // =================================== ABA 1: 2. Personalidade da IA
                        ColumnLayout {
                            visible: communicationAgentModal.currentNavTab === 1
                            Layout.fillWidth: true
                            spacing: 16

                            // Linha 1: Tom de voz e Nível de formalidade
                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 16

                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 4

                                    Text { text: "Tom de voz *"; color: textPrimary; font.pixelSize: 11; font.weight: Font.DemiBold }
                                    ComboBox {
                                        id: caToneBox
                                        Layout.fillWidth: true
                                        Layout.preferredHeight: 40
                                        model: ["Selecione o tom de voz", "Acolhedor", "Amigável", "Calmo", "Direto", "Empático", "Entusiasmado", "Persuasivo", "Técnico"]
                                        font.pixelSize: 11
                                        delegate: ItemDelegate {
                                            width: caToneBox.width; height: 36
                                            highlighted: caToneBox.highlightedIndex === index
                                            contentItem: Text { text: modelData; color: window.isDark ? "#EAFBFF" : "#0F172A"; font.pixelSize: 11; verticalAlignment: Text.AlignVCenter }
                                            background: Rectangle { color: parent.highlighted ? (window.isDark ? "#14364C" : "#E0F2FE") : (window.isDark ? "#0A152A" : "#FFFFFF") }
                                        }
                                        contentItem: Text { leftPadding: 12; rightPadding: 28; text: caToneBox.displayText; color: textPrimary; font.pixelSize: 11; verticalAlignment: Text.AlignVCenter }
                                        background: Rectangle { radius: 8; color: window.isDark ? "#0D1D33" : "#FFFFFF"; border.color: caToneBox.activeFocus || caToneBox.popup.visible ? green : (window.isDark ? "#23435E" : "#CBD5E1") }
                                        popup: Popup {
                                            y: caToneBox.height + 4; width: caToneBox.width; implicitHeight: Math.min(contentItem.implicitHeight + 4, 260); padding: 2
                                            contentItem: ListView { clip: true; implicitHeight: contentHeight; model: caToneBox.popup.visible ? caToneBox.delegateModel : null; currentIndex: caToneBox.highlightedIndex; ScrollIndicator.vertical: ScrollIndicator {} }
                                            background: Rectangle { radius: 8; color: window.isDark ? "#0A152A" : "#FFFFFF"; border.color: window.isDark ? "#23435E" : "#CBD5E1"; border.width: 1 }
                                        }
                                    }
                                }

                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 4

                                    Text { text: "Nível de formalidade *"; color: textPrimary; font.pixelSize: 11; font.weight: Font.DemiBold }
                                    ComboBox {
                                        id: caFormalityBox
                                        Layout.fillWidth: true
                                        Layout.preferredHeight: 40
                                        model: ["Selecione o nível de formalidade", "Informal", "Equilibrado", "Formal"]
                                        font.pixelSize: 11
                                        delegate: ItemDelegate {
                                            width: caFormalityBox.width; height: 36
                                            highlighted: caFormalityBox.highlightedIndex === index
                                            contentItem: Text { text: modelData; color: window.isDark ? "#EAFBFF" : "#0F172A"; font.pixelSize: 11; verticalAlignment: Text.AlignVCenter }
                                            background: Rectangle { color: parent.highlighted ? (window.isDark ? "#14364C" : "#E0F2FE") : (window.isDark ? "#0A152A" : "#FFFFFF") }
                                        }
                                        contentItem: Text { leftPadding: 12; rightPadding: 28; text: caFormalityBox.displayText; color: textPrimary; font.pixelSize: 11; verticalAlignment: Text.AlignVCenter }
                                        background: Rectangle { radius: 8; color: window.isDark ? "#0D1D33" : "#FFFFFF"; border.color: caFormalityBox.activeFocus || caFormalityBox.popup.visible ? green : (window.isDark ? "#23435E" : "#CBD5E1") }
                                        popup: Popup {
                                            y: caFormalityBox.height + 4; width: caFormalityBox.width; implicitHeight: Math.min(contentItem.implicitHeight + 4, 220); padding: 2
                                            contentItem: ListView { clip: true; implicitHeight: contentHeight; model: caFormalityBox.popup.visible ? caFormalityBox.delegateModel : null; currentIndex: caFormalityBox.highlightedIndex; ScrollIndicator.vertical: ScrollIndicator {} }
                                            background: Rectangle { radius: 8; color: window.isDark ? "#0A152A" : "#FFFFFF"; border.color: window.isDark ? "#23435E" : "#CBD5E1"; border.width: 1 }
                                        }
                                    }
                                }
                            }

                            // Linha 2: Uso de emojis * (4 cards como no print)
                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 8

                                Text { text: "Uso de emojis *"; color: textPrimary; font.pixelSize: 11; font.weight: Font.DemiBold }

                                RowLayout {
                                    Layout.fillWidth: true
                                    spacing: 12

                                    Repeater {
                                        model: [
                                            {"level": "Nunca", "icon": "😐"},
                                            {"level": "Pouco", "icon": "🙂"},
                                            {"level": "Normal", "icon": "😄"},
                                            {"level": "Muito", "icon": "🤩"}
                                        ]

                                        delegate: Rectangle {
                                            Layout.fillWidth: true
                                            Layout.preferredHeight: 74
                                            radius: 10
                                            property bool isSelected: communicationAgentModal.selectedEmojiLevel === modelData.level
                                            color: isSelected ? (window.isDark ? "#0E2B22" : "#E6F7F2") : (window.isDark ? "#070E1B" : "#FFFFFF")
                                            border.color: isSelected ? (window.isDark ? "#1E824C" : "#A3E6CD") : (window.isDark ? "#152A40" : "#CBD5E1")
                                            border.width: isSelected ? 1.5 : 1

                                            Column {
                                                anchors.centerIn: parent
                                                spacing: 6
                                                Text { anchors.horizontalCenter: parent.horizontalCenter; text: modelData.icon; font.pixelSize: 20 }
                                                Text {
                                                    anchors.horizontalCenter: parent.horizontalCenter
                                                    text: modelData.level
                                                    color: parent.parent.isSelected ? (window.isDark ? "#4EF2A6" : "#00875A") : textPrimary
                                                    font.pixelSize: 10
                                                    font.weight: parent.parent.isSelected ? Font.Bold : Font.Normal
                                                }
                                            }

                                            MouseArea {
                                                anchors.fill: parent
                                                cursorShape: Qt.PointingHandCursor
                                                onClicked: communicationAgentModal.selectedEmojiLevel = modelData.level
                                            }
                                        }
                                    }
                                }
                            }

                            // Linha 3: Estilo das respostas e Linguagem
                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 16

                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 4

                                    Text { text: "Estilo das respostas *"; color: textPrimary; font.pixelSize: 11; font.weight: Font.DemiBold }
                                    ComboBox {
                                        id: caResponseStyleBox
                                        Layout.fillWidth: true
                                        Layout.preferredHeight: 40
                                        model: ["Selecione o estilo das respostas", "Curto e objetivo", "Equilibrado", "Detalhado", "Consultivo", "Passo a passo"]
                                        font.pixelSize: 11
                                        delegate: ItemDelegate {
                                            width: caResponseStyleBox.width; height: 36
                                            highlighted: caResponseStyleBox.highlightedIndex === index
                                            contentItem: Text { text: modelData; color: window.isDark ? "#EAFBFF" : "#0F172A"; font.pixelSize: 11; verticalAlignment: Text.AlignVCenter }
                                            background: Rectangle { color: parent.highlighted ? (window.isDark ? "#14364C" : "#E0F2FE") : (window.isDark ? "#0A152A" : "#FFFFFF") }
                                        }
                                        contentItem: Text { leftPadding: 12; rightPadding: 28; text: caResponseStyleBox.displayText; color: textPrimary; font.pixelSize: 11; verticalAlignment: Text.AlignVCenter }
                                        background: Rectangle { radius: 8; color: window.isDark ? "#0D1D33" : "#FFFFFF"; border.color: caResponseStyleBox.activeFocus || caResponseStyleBox.popup.visible ? green : (window.isDark ? "#23435E" : "#CBD5E1") }
                                        popup: Popup {
                                            y: caResponseStyleBox.height + 4; width: caResponseStyleBox.width; implicitHeight: Math.min(contentItem.implicitHeight + 4, 240); padding: 2
                                            contentItem: ListView { clip: true; implicitHeight: contentHeight; model: caResponseStyleBox.popup.visible ? caResponseStyleBox.delegateModel : null; currentIndex: caResponseStyleBox.highlightedIndex; ScrollIndicator.vertical: ScrollIndicator {} }
                                            background: Rectangle { radius: 8; color: window.isDark ? "#0A152A" : "#FFFFFF"; border.color: window.isDark ? "#23435E" : "#CBD5E1"; border.width: 1 }
                                        }
                                    }
                                }

                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 4

                                    Text { text: "Linguagem *"; color: textPrimary; font.pixelSize: 11; font.weight: Font.DemiBold }
                                    ComboBox {
                                        id: caLanguageBox
                                        Layout.fillWidth: true
                                        Layout.preferredHeight: 40
                                        model: ["Português (Brasil)", "Inglês", "Espanhol", "Francês", "Alemão", "Italiano"]
                                        font.pixelSize: 11
                                        delegate: ItemDelegate {
                                            width: caLanguageBox.width; height: 36
                                            highlighted: caLanguageBox.highlightedIndex === index
                                            contentItem: Text { text: modelData; color: window.isDark ? "#EAFBFF" : "#0F172A"; font.pixelSize: 11; verticalAlignment: Text.AlignVCenter }
                                            background: Rectangle { color: parent.highlighted ? (window.isDark ? "#14364C" : "#E0F2FE") : (window.isDark ? "#0A152A" : "#FFFFFF") }
                                        }
                                        contentItem: Text { leftPadding: 12; rightPadding: 28; text: caLanguageBox.displayText; color: textPrimary; font.pixelSize: 11; verticalAlignment: Text.AlignVCenter }
                                        background: Rectangle { radius: 8; color: window.isDark ? "#0D1D33" : "#FFFFFF"; border.color: caLanguageBox.activeFocus || caLanguageBox.popup.visible ? green : (window.isDark ? "#23435E" : "#CBD5E1") }
                                        popup: Popup {
                                            y: caLanguageBox.height + 4; width: caLanguageBox.width; implicitHeight: Math.min(contentItem.implicitHeight + 4, 240); padding: 2
                                            contentItem: ListView { clip: true; implicitHeight: contentHeight; model: caLanguageBox.popup.visible ? caLanguageBox.delegateModel : null; currentIndex: caLanguageBox.highlightedIndex; ScrollIndicator.vertical: ScrollIndicator {} }
                                            background: Rectangle { radius: 8; color: window.isDark ? "#0A152A" : "#FFFFFF"; border.color: window.isDark ? "#23435E" : "#CBD5E1"; border.width: 1 }
                                        }
                                    }
                                }
                            }
                        }

                        // =================================== ABA 2: 3. Função da IA na empresa
                        ColumnLayout {
                            visible: communicationAgentModal.currentNavTab === 2
                            Layout.fillWidth: true
                            spacing: 16

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 6

                                RowLayout {
                                    Layout.fillWidth: true
                                    Text { text: "Descrição da função *"; color: textPrimary; font.pixelSize: 11; font.weight: Font.DemiBold }
                                    Item { Layout.fillWidth: true }
                                    Text { text: caJobDescArea.text.length + "/1000"; color: textMuted; font.pixelSize: 9 }
                                }

                                Rectangle {
                                    Layout.fillWidth: true
                                    Layout.preferredHeight: 140
                                    radius: 8
                                    color: window.isDark ? "#0D1D33" : "#FFFFFF"
                                    border.color: caJobDescArea.activeFocus ? green : (window.isDark ? "#23435E" : "#CBD5E1")

                                    ScrollView {
                                        anchors.fill: parent
                                        anchors.margins: 10
                                        clip: true

                                        TextArea {
                                            id: caJobDescArea
                                            color: textPrimary
                                            font.pixelSize: 11
                                            wrapMode: TextArea.Wrap
                                            placeholderText: "Ex.: Atender clientes interessados em produtos e serviços, tirar dúvidas e gerar orçamentos."
                                            placeholderTextColor: window.isDark ? "#526D83" : "#94A3B8"
                                            background: null
                                        }
                                    }
                                }

                                RowLayout {
                                    Layout.fillWidth: true
                                    Item { Layout.fillWidth: true }

                                    JarvisButton {
                                        variant: "secondary"
                                        text: "+  Escolher função pronta  ▼"
                                        implicitHeight: 32
                                        leftPadding: 12; rightPadding: 12
                                        textSize: 8
                                        onClicked: presetMenu.open()

                                        Menu {
                                            id: presetMenu
                                            MenuItem {
                                                text: "Atendimento & Vendas Comerciais"
                                                onTriggered: caJobDescArea.text = "Atender clientes interessados em produtos e serviços, apresentar opções do catálogo, tirar dúvidas técnicas e comerciais e gerar orçamentos."
                                            }
                                            MenuItem {
                                                text: "Suporte Técnico Especializado"
                                                onTriggered: caJobDescArea.text = "Prestar assistência e suporte técnico aos clientes, diagnosticar problemas de uso, orientar soluções passo a passo e abrir chamados quando necessário."
                                            }
                                            MenuItem {
                                                text: "Agendamento & Reservas"
                                                onTriggered: caJobDescArea.text = "Receber solicitações de agendamento de consultas ou reuniões, confirmar disponibilidade de horários e registrar compromissos."
                                            }
                                            MenuItem {
                                                text: "Recepção Geral & Triagem"
                                                onTriggered: caJobDescArea.text = "Dar boas-vindas aos clientes, entender a necessidade inicial e direcionar para o setor ou responsável correto."
                                            }
                                        }
                                    }
                                }
                            }

                            // Principais responsabilidades
                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 8

                                RowLayout {
                                    Layout.fillWidth: true
                                    Text { text: "Principais responsabilidades"; color: textPrimary; font.pixelSize: 11; font.weight: Font.DemiBold }
                                    Item { Layout.fillWidth: true }
                                    JarvisButton {
                                        variant: "secondary"
                                        text: "+  Adicionar responsabilidade"
                                        implicitHeight: 30
                                        leftPadding: 10; rightPadding: 10
                                        textSize: 8
                                        onClicked: {
                                            var copy = communicationAgentModal.responsibilitiesList.slice()
                                            copy.push("Nova responsabilidade...")
                                            communicationAgentModal.responsibilitiesList = copy
                                        }
                                    }
                                }

                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 6

                                    Repeater {
                                        model: communicationAgentModal.responsibilitiesList

                                        delegate: RowLayout {
                                            Layout.fillWidth: true
                                            spacing: 8

                                            Text { text: "•"; color: green; font.pixelSize: 14; font.weight: Font.Bold }

                                            TextField {
                                                Layout.fillWidth: true
                                                Layout.preferredHeight: 36
                                                text: modelData
                                                color: textPrimary
                                                font.pixelSize: 10
                                                leftPadding: 10
                                                background: Rectangle {
                                                    radius: 6
                                                    color: window.isDark ? "#0D1D33" : "#FFFFFF"
                                                    border.color: parent.activeFocus ? green : (window.isDark ? "#23435E" : "#CBD5E1")
                                                }
                                                onTextChanged: {
                                                    communicationAgentModal.responsibilitiesList[index] = text
                                                }
                                            }

                                            JarvisButton {
                                                variant: "danger"
                                                text: "🗑"
                                                width: 30; height: 30
                                                textSize: 10
                                                onClicked: {
                                                    var copy = communicationAgentModal.responsibilitiesList.slice()
                                                    copy.splice(index, 1)
                                                    communicationAgentModal.responsibilitiesList = copy
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }

                        // =================================== ABA 3: 4. Sobre a empresa
                        ColumnLayout {
                            visible: communicationAgentModal.currentNavTab === 3
                            Layout.fillWidth: true
                            spacing: 16

                            // Linha 1: Nome da empresa * e Segmento *
                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 16

                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 4

                                    Text { text: "Nome da empresa *"; color: textPrimary; font.pixelSize: 11; font.weight: Font.DemiBold }
                                    TextField {
                                        id: caCompanyNameField
                                        Layout.fillWidth: true
                                        Layout.preferredHeight: 40
                                        placeholderText: "Ex.: Empresa Fictícia Aurora"
                                        placeholderTextColor: window.isDark ? "#526D83" : "#94A3B8"
                                        color: textPrimary
                                        font.pixelSize: 11
                                        leftPadding: 12
                                        background: Rectangle {
                                            radius: 8
                                            color: window.isDark ? "#0D1D33" : "#FFFFFF"
                                            border.color: parent.activeFocus ? green : (window.isDark ? "#23435E" : "#CBD5E1")
                                        }
                                    }
                                }

                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 4

                                    Text { text: "Segmento *"; color: textPrimary; font.pixelSize: 11; font.weight: Font.DemiBold }
                                    TextField {
                                        id: caCompanySegmentField
                                        Layout.fillWidth: true
                                        Layout.preferredHeight: 40
                                        placeholderText: "Ex.: Soluções criativas"
                                        placeholderTextColor: window.isDark ? "#526D83" : "#94A3B8"
                                        color: textPrimary
                                        font.pixelSize: 11
                                        leftPadding: 12
                                        background: Rectangle {
                                            radius: 8
                                            color: window.isDark ? "#0D1D33" : "#FFFFFF"
                                            border.color: parent.activeFocus ? green : (window.isDark ? "#23435E" : "#CBD5E1")
                                        }
                                    }
                                }
                            }

                            // Linha 2: Descrição da empresa *
                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 4

                                RowLayout {
                                    Layout.fillWidth: true
                                    Text { text: "Descrição da empresa *"; color: textPrimary; font.pixelSize: 11; font.weight: Font.DemiBold }
                                    Item { Layout.fillWidth: true }
                                    Text { text: caCompanyDescArea.text.length + "/1500"; color: textMuted; font.pixelSize: 9 }
                                }

                                Rectangle {
                                    Layout.fillWidth: true
                                    Layout.preferredHeight: 110
                                    radius: 8
                                    color: window.isDark ? "#0D1D33" : "#FFFFFF"
                                    border.color: caCompanyDescArea.activeFocus ? green : (window.isDark ? "#23435E" : "#CBD5E1")

                                    ScrollView {
                                        anchors.fill: parent
                                        anchors.margins: 10
                                        clip: true

                                        TextArea {
                                            id: caCompanyDescArea
                                            color: textPrimary
                                            font.pixelSize: 11
                                            wrapMode: TextArea.Wrap
                                            placeholderText: "Fale sobre a história, missão, visão, valores e diferenciais."
                                            placeholderTextColor: window.isDark ? "#526D83" : "#94A3B8"
                                            background: null
                                        }
                                    }
                                }
                            }

                            // Linha 3: Produtos e serviços *
                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 4

                                RowLayout {
                                    Layout.fillWidth: true
                                    Text { text: "Produtos e serviços *"; color: textPrimary; font.pixelSize: 11; font.weight: Font.DemiBold }
                                    Item { Layout.fillWidth: true }
                                    Text { text: caCompanyProductsArea.text.length + "/1000"; color: textMuted; font.pixelSize: 9 }
                                }

                                Rectangle {
                                    Layout.fillWidth: true
                                    Layout.preferredHeight: 110
                                    radius: 8
                                    color: window.isDark ? "#0D1D33" : "#FFFFFF"
                                    border.color: caCompanyProductsArea.activeFocus ? green : (window.isDark ? "#23435E" : "#CBD5E1")

                                    ScrollView {
                                        anchors.fill: parent
                                        anchors.margins: 10
                                        clip: true

                                        TextArea {
                                            id: caCompanyProductsArea
                                            color: textPrimary
                                            font.pixelSize: 11
                                            wrapMode: TextArea.Wrap
                                            placeholderText: "Liste os principais produtos e serviços oferecidos."
                                            placeholderTextColor: window.isDark ? "#526D83" : "#94A3B8"
                                            background: null
                                        }
                                    }
                                }
                            }

                            // Linha 4: Público-alvo e Regiões atendidas
                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 16

                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 4

                                    Text { text: "Público-alvo"; color: textPrimary; font.pixelSize: 11; font.weight: Font.DemiBold }
                                    TextField {
                                        id: caCompanyAudienceField
                                        Layout.fillWidth: true
                                        Layout.preferredHeight: 40
                                        placeholderText: "Ex.: Empresas, lojas, franquias e indústrias"
                                        placeholderTextColor: window.isDark ? "#526D83" : "#94A3B8"
                                        color: textPrimary
                                        font.pixelSize: 11
                                        leftPadding: 12
                                        background: Rectangle {
                                            radius: 8
                                            color: window.isDark ? "#0D1D33" : "#FFFFFF"
                                            border.color: parent.activeFocus ? green : (window.isDark ? "#23435E" : "#CBD5E1")
                                        }
                                    }
                                }

                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 4

                                    Text { text: "Regiões atendidas"; color: textPrimary; font.pixelSize: 11; font.weight: Font.DemiBold }
                                    TextField {
                                        id: caCompanyRegionsField
                                        Layout.fillWidth: true
                                        Layout.preferredHeight: 40
                                        placeholderText: "Ex.: Cidade Alfa e regiões próximas"
                                        placeholderTextColor: window.isDark ? "#526D83" : "#94A3B8"
                                        color: textPrimary
                                        font.pixelSize: 11
                                        leftPadding: 12
                                        background: Rectangle {
                                            radius: 8
                                            color: window.isDark ? "#0D1D33" : "#FFFFFF"
                                            border.color: parent.activeFocus ? green : (window.isDark ? "#23435E" : "#CBD5E1")
                                        }
                                    }
                                }
                            }

                            // Linha 5: Horário de atendimento e Formas de pagamento
                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 16

                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 4

                                    Text { text: "Horário de atendimento"; color: textPrimary; font.pixelSize: 11; font.weight: Font.DemiBold }
                                    TextField {
                                        id: caCompanyHoursField
                                        Layout.fillWidth: true
                                        Layout.preferredHeight: 40
                                        placeholderText: "Ex.: Segunda a sexta, 08h às 18h"
                                        placeholderTextColor: window.isDark ? "#526D83" : "#94A3B8"
                                        color: textPrimary
                                        font.pixelSize: 11
                                        leftPadding: 12
                                        background: Rectangle {
                                            radius: 8
                                            color: window.isDark ? "#0D1D33" : "#FFFFFF"
                                            border.color: parent.activeFocus ? green : (window.isDark ? "#23435E" : "#CBD5E1")
                                        }
                                    }
                                }

                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 4

                                    Text { text: "Formas de pagamento"; color: textPrimary; font.pixelSize: 11; font.weight: Font.DemiBold }
                                    TextField {
                                        id: caCompanyPaymentField
                                        Layout.fillWidth: true
                                        Layout.preferredHeight: 40
                                        placeholderText: "Ex.: Pix, boleto, cartão e transferência"
                                        placeholderTextColor: window.isDark ? "#526D83" : "#94A3B8"
                                        color: textPrimary
                                        font.pixelSize: 11
                                        leftPadding: 12
                                        background: Rectangle {
                                            radius: 8
                                            color: window.isDark ? "#0D1D33" : "#FFFFFF"
                                            border.color: parent.activeFocus ? green : (window.isDark ? "#23435E" : "#CBD5E1")
                                        }
                                    }
                                }
                            }

                            // Linha 6: Políticas e regras (Opcional)
                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 4

                                RowLayout {
                                    Layout.fillWidth: true
                                    Row {
                                        spacing: 6
                                        Text { text: "Políticas e regras"; color: textPrimary; font.pixelSize: 11; font.weight: Font.DemiBold }
                                        Text { text: "Opcional"; color: textMuted; font.pixelSize: 9 }
                                    }
                                    Item { Layout.fillWidth: true }
                                    Text { text: caCompanyPoliciesArea.text.length + "/1000"; color: textMuted; font.pixelSize: 9 }
                                }

                                Rectangle {
                                    Layout.fillWidth: true
                                    Layout.preferredHeight: 110
                                    radius: 8
                                    color: window.isDark ? "#0D1D33" : "#FFFFFF"
                                    border.color: caCompanyPoliciesArea.activeFocus ? green : (window.isDark ? "#23435E" : "#CBD5E1")

                                    ScrollView {
                                        anchors.fill: parent
                                        anchors.margins: 10
                                        clip: true

                                        TextArea {
                                            id: caCompanyPoliciesArea
                                            color: textPrimary
                                            font.pixelSize: 11
                                            wrapMode: TextArea.Wrap
                                            placeholderText: "Informe políticas, prazos, garantias e regras de devolução."
                                            placeholderTextColor: window.isDark ? "#526D83" : "#94A3B8"
                                            background: null
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }

            Rectangle { Layout.fillWidth: true; height: 1; color: window.isDark ? "#142840" : "#E2E8F0" }

            // Footer do Modal
            RowLayout {
                Layout.fillWidth: true
                spacing: 12

                Item { Layout.fillWidth: true }

                JarvisButton {
                    variant: "secondary"
                    text: "✕  Cancelar"
                    implicitHeight: 40
                    implicitWidth: 120
                    onClicked: communicationAgentModal.close()
                }

                JarvisButton {
                    variant: "save"
                    text: "✔  Salvar Agente IA"
                    implicitHeight: 40
                    leftPadding: 24; rightPadding: 24
                    onClicked: {
                        var chosenModelId = 0
                        var chosenModelName = ""
                        var agents = jarvisBackend.aiAgents || []
                        if (agents.length > 0 && caModelBox.currentIndex >= 0 && caModelBox.currentIndex < agents.length) {
                            chosenModelId = agents[caModelBox.currentIndex].id || 0
                            chosenModelName = (agents[caModelBox.currentIndex].provider || "OpenAI") + " // " + (agents[caModelBox.currentIndex].model || "")
                        }

                        jarvisBackend.saveCommunicationAgent(
                            communicationAgentModal.editingId,
                            caNameField.text,
                            caAgeField.text,
                            caGenderBox.currentText === "Selecione o gênero" ? "" : caGenderBox.currentText,
                            caRoleField.text,
                            chosenModelId,
                            chosenModelName,
                            caToneBox.currentText === "Selecione o tom de voz" ? "" : caToneBox.currentText,
                            caFormalityBox.currentText === "Selecione o nível de formalidade" ? "" : caFormalityBox.currentText,
                            communicationAgentModal.selectedEmojiLevel,
                            caResponseStyleBox.currentText === "Selecione o estilo das respostas" ? "" : caResponseStyleBox.currentText,
                            caLanguageBox.currentText,
                            caJobDescArea.text,
                            JSON.stringify(communicationAgentModal.responsibilitiesList),
                            caCompanyNameField.text,
                            caCompanySegmentField.text,
                            caCompanyDescArea.text,
                            caCompanyProductsArea.text,
                            caCompanyAudienceField.text,
                            caCompanyRegionsField.text,
                            caCompanyHoursField.text,
                            caCompanyPaymentField.text,
                            caCompanyPoliciesArea.text,
                            caActiveSwitch.checked
                        )
                        communicationAgentModal.close()
                    }
                }
            }
        }
    }

    // =========================================================================
    // MODAL: GESTÃO DE MEMÓRIA CONTEXTUAL & APRENDIZAGEM COMPORTAMENTAL GLOBAL
    // =========================================================================
    Popup {
        id: memoryManagerModal
        parent: Overlay.overlay
        anchors.centerIn: parent
        width: Math.min(window.width - 60, 960)
        height: Math.min(window.height - 40, 680)
        modal: true
        focus: true
        padding: 0
        closePolicy: Popup.CloseOnEscape

        property int memoryTab: 0
        property string filterCategory: "todos"
        property string searchText: ""
        property bool showAddForm: false

        Overlay.modal: Rectangle {
            color: window.isDark ? "#E6030714" : "#80000000"
        }

        background: Rectangle {
            radius: 16
            color: window.isDark ? "#070E1C" : "#FFFFFF"
            border.color: window.isDark ? "#1C3B5E" : "#CBD5E1"
            border.width: 1
        }

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 20
            spacing: 14

            // Header
            RowLayout {
                Layout.fillWidth: true
                spacing: 12

                Rectangle {
                    Layout.alignment: Qt.AlignVCenter
                    width: 42; height: 42; radius: 21
                    color: window.isDark ? "#122A42" : "#E0F2FE"
                    border.color: cyan
                    border.width: 1
                    Text { anchors.centerIn: parent; text: "🧠"; font.pixelSize: 20 }
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignVCenter
                    spacing: 2
                    Text {
                        text: "MEMÓRIA CONTEXTUAL & APRENDIZADO"
                        color: textPrimary
                        font.pixelSize: 14
                        font.weight: Font.Bold
                        font.letterSpacing: 1.2
                    }
                    Text {
                        Layout.fillWidth: true
                        text: "Conhecimentos, preferências e hábitos aprendidos com as suas conversas em todo o sistema."
                        color: textMuted
                        font.pixelSize: 10
                        wrapMode: Text.Wrap
                    }
                }

                Rectangle {
                    Layout.alignment: Qt.AlignVCenter
                    Layout.preferredWidth: 32
                    Layout.preferredHeight: 32
                    radius: 16
                    color: closeMemMouse.containsMouse ? (window.isDark ? "#3A1622" : "#FEE2E2") : "transparent"
                    border.color: closeMemMouse.containsMouse ? "#EF4444" : "transparent"
                    Text { anchors.centerIn: parent; text: "✕"; color: closeMemMouse.containsMouse ? "#EF4444" : textMuted; font.pixelSize: 14 }
                    MouseArea {
                        id: closeMemMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: memoryManagerModal.close()
                    }
                }
            }

            Rectangle { Layout.fillWidth: true; height: 1; color: window.isDark ? "#142840" : "#E2E8F0" }

            // Abas de Navegação
            RowLayout {
                Layout.fillWidth: true
                spacing: 8

                Rectangle {
                    Layout.preferredWidth: 240
                    Layout.preferredHeight: 38
                    radius: 8
                    color: memoryManagerModal.memoryTab === 0 ? (window.isDark ? "#13314D" : "#E0F2FE") : "transparent"
                    border.color: memoryManagerModal.memoryTab === 0 ? cyan : "transparent"
                    RowLayout {
                        anchors.centerIn: parent
                        spacing: 8
                        Text { text: "🧠"; font.pixelSize: 13 }
                        Text {
                            text: "Memórias Consolidadas (" + (jarvisBackend.learnedMemories ? jarvisBackend.learnedMemories.length : 0) + ")"
                            color: memoryManagerModal.memoryTab === 0 ? cyan : textMuted
                            font.pixelSize: 11
                            font.weight: Font.DemiBold
                        }
                    }
                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: memoryManagerModal.memoryTab = 0
                    }
                }

                Rectangle {
                    Layout.preferredWidth: 230
                    Layout.preferredHeight: 38
                    radius: 8
                    color: memoryManagerModal.memoryTab === 1 ? (window.isDark ? "#13314D" : "#E0F2FE") : "transparent"
                    border.color: memoryManagerModal.memoryTab === 1 ? cyan : "transparent"
                    RowLayout {
                        anchors.centerIn: parent
                        spacing: 8
                        Text { text: "📊"; font.pixelSize: 13 }
                        Text {
                            text: "Aprendizagem Comportamental"
                            color: memoryManagerModal.memoryTab === 1 ? cyan : textMuted
                            font.pixelSize: 11
                            font.weight: Font.DemiBold
                        }
                    }
                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: memoryManagerModal.memoryTab = 1
                    }
                }

                Item { Layout.fillWidth: true }

                JarvisButton {
                    variant: "secondary"
                    text: "↻  Atualizar"
                    implicitHeight: 32
                    textSize: 8
                    leftPadding: 10; rightPadding: 10
                    onClicked: jarvisBackend.refreshCognition()
                }
            }

            // ========================================== TAB 0: MEMÓRIAS CONSOLIDADAS
            ColumnLayout {
                visible: memoryManagerModal.memoryTab === 0
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: 12

                // Barra de Busca e Ações
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 10

                    TextField {
                        id: memSearchField
                        Layout.fillWidth: true
                        Layout.preferredHeight: 38
                        placeholderText: "🔍  Filtrar memórias por texto ou categoria..."
                        placeholderTextColor: window.isDark ? "#526D83" : "#94A3B8"
                        color: textPrimary
                        font.pixelSize: 11
                        leftPadding: 12
                        background: Rectangle {
                            radius: 8
                            color: window.isDark ? "#0A172B" : "#F8FAFC"
                            border.color: parent.activeFocus ? cyan : (window.isDark ? "#1E3B5C" : "#CBD5E1")
                        }
                        onTextChanged: memoryManagerModal.searchText = text
                    }

                    JarvisButton {
                        variant: memoryManagerModal.showAddForm ? "danger" : "success"
                        text: memoryManagerModal.showAddForm ? "✕ Fechar Formulário" : "+  Adicionar Memória"
                        implicitHeight: 38
                        textSize: 9
                        onClicked: memoryManagerModal.showAddForm = !memoryManagerModal.showAddForm
                    }

                    JarvisButton {
                        variant: "danger"
                        text: "🗑 Limpar Todas"
                        implicitHeight: 38
                        textSize: 9
                        visible: jarvisBackend.learnedMemories && jarvisBackend.learnedMemories.length > 0
                        onClicked: jarvisBackend.clearLearnedMemories()
                    }
                }

                // Formulário Inline de Adicionar Nova Memória
                Rectangle {
                    visible: memoryManagerModal.showAddForm
                    Layout.fillWidth: true
                    implicitHeight: newMemCol.implicitHeight + 24
                    radius: 10
                    color: window.isDark ? "#0A182E" : "#F0F9FF"
                    border.color: cyan
                    border.width: 1

                    ColumnLayout {
                        id: newMemCol
                        anchors.fill: parent
                        anchors.margins: 12
                        spacing: 10

                        Text {
                            text: "Adicionar Conhecimento Manual"
                            color: cyan
                            font.pixelSize: 11
                            font.weight: Font.DemiBold
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10

                            ComboBox {
                                id: newMemCatBox
                                Layout.preferredWidth: 160
                                Layout.preferredHeight: 36
                                model: ["preferencia", "fato", "projeto", "regra", "empresa"]
                                font.pixelSize: 10
                            }

                            TextField {
                                id: newMemKeyField
                                Layout.preferredWidth: 200
                                Layout.preferredHeight: 36
                                placeholderText: "Chave identificadora (ex: pref_linguagem)"
                                placeholderTextColor: window.isDark ? "#526D83" : "#94A3B8"
                                color: textPrimary
                                font.pixelSize: 10
                                background: Rectangle {
                                    radius: 6
                                    color: window.isDark ? "#060D19" : "#FFFFFF"
                                    border.color: window.isDark ? "#1C3652" : "#CBD5E1"
                                }
                            }

                            TextField {
                                id: newMemContentField
                                Layout.fillWidth: true
                                Layout.preferredHeight: 36
                                placeholderText: "Conteúdo (ex: O usuário prefere respostas em Python com comentários)"
                                placeholderTextColor: window.isDark ? "#526D83" : "#94A3B8"
                                color: textPrimary
                                font.pixelSize: 10
                                background: Rectangle {
                                    radius: 6
                                    color: window.isDark ? "#060D19" : "#FFFFFF"
                                    border.color: window.isDark ? "#1C3652" : "#CBD5E1"
                                }
                            }

                            JarvisButton {
                                variant: "save"
                                text: "✔ Salvar"
                                implicitHeight: 36
                                textSize: 9
                                onClicked: {
                                    if (newMemContentField.text.trim().length > 0) {
                                        jarvisBackend.saveLearnedMemory(
                                            0,
                                            newMemCatBox.currentText,
                                            newMemKeyField.text,
                                            newMemContentField.text
                                        )
                                        newMemKeyField.text = ""
                                        newMemContentField.text = ""
                                        memoryManagerModal.showAddForm = false
                                    }
                                }
                            }
                        }
                    }
                }

                // Lista de Memórias
                ScrollView {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    contentWidth: availableWidth
                    clip: true

                    ColumnLayout {
                        width: parent.width
                        spacing: 8

                        // Empty State
                        Rectangle {
                            visible: !jarvisBackend.learnedMemories || jarvisBackend.learnedMemories.length === 0
                            Layout.fillWidth: true
                            implicitHeight: 200
                            radius: 12
                            color: window.isDark ? "#0A172B" : "#F8FAFC"
                            border.color: window.isDark ? "#183650" : "#CBD5E1"

                            ColumnLayout {
                                anchors.centerIn: parent
                                spacing: 10

                                Text { text: "🧠"; font.pixelSize: 28; Layout.alignment: Qt.AlignHCenter }
                                Text {
                                    text: "Nenhuma memória registrada ainda"
                                    color: textPrimary
                                    font.pixelSize: 13
                                    font.weight: Font.DemiBold
                                    Layout.alignment: Qt.AlignHCenter
                                }
                                Text {
                                    text: "Conforme você conversa, ele aprende automaticamente suas preferências, fatos, regras e projetos."
                                    color: textMuted
                                    font.pixelSize: 10
                                    Layout.alignment: Qt.AlignHCenter
                                }
                            }
                        }

                        Repeater {
                            model: {
                                var all = jarvisBackend.learnedMemories || []
                                if (!memoryManagerModal.searchText) return all
                                var q = memoryManagerModal.searchText.toLowerCase()
                                return all.filter(function(m) {
                                    return (m.content && m.content.toLowerCase().indexOf(q) >= 0) ||
                                           (m.category && m.category.toLowerCase().indexOf(q) >= 0) ||
                                           (m.key && m.key.toLowerCase().indexOf(q) >= 0)
                                })
                            }
                            delegate: Rectangle {
                                Layout.fillWidth: true
                                implicitHeight: memCardCol.implicitHeight + 20
                                radius: 10
                                color: window.isDark ? "#0A172A" : "#FFFFFF"
                                border.color: window.isDark ? "#16314D" : "#E2E8F0"
                                border.width: 1

                                ColumnLayout {
                                    id: memCardCol
                                    anchors.fill: parent
                                    anchors.margins: 12
                                    spacing: 6

                                    RowLayout {
                                        Layout.fillWidth: true
                                        spacing: 8

                                        Rectangle {
                                            implicitHeight: 20
                                            implicitWidth: catLabel.implicitWidth + 12
                                            radius: 4
                                            color: modelData.category === "preferencia" ? (window.isDark ? "#122A42" : "#E0F2FE")
                                                 : modelData.category === "regra" ? (window.isDark ? "#331622" : "#FEE2E2")
                                                 : modelData.category === "projeto" ? (window.isDark ? "#1F1633" : "#F3E8FF")
                                                 : (window.isDark ? "#10281F" : "#DCFCE7")
                                            Text {
                                                id: catLabel
                                                anchors.centerIn: parent
                                                text: (modelData.category || "fato").toUpperCase()
                                                color: modelData.category === "preferencia" ? cyan
                                                     : modelData.category === "regra" ? "#EF4444"
                                                     : modelData.category === "projeto" ? violet
                                                     : green
                                                font.pixelSize: 8
                                                font.weight: Font.Bold
                                            }
                                        }

                                        Text {
                                            text: modelData.key ? ("#" + modelData.key) : ""
                                            color: textMuted
                                            font.pixelSize: 9
                                            elide: Text.ElideRight
                                        }

                                        Text {
                                            visible: text !== ""
                                            text: {
                                                var s = modelData.source || ""
                                                if (s === "manual") return "✍️ você"
                                                if (s === "consolidacao_llm") return "🧠 IA"
                                                if (s === "aprendizado_dialogo") return "💬 conversa"
                                                return ""
                                            }
                                            color: textMuted
                                            font.pixelSize: 8
                                        }

                                        Item { Layout.fillWidth: true }

                                        Text {
                                            text: "Acessado " + (modelData.access_count || 0) + "x"
                                            color: textMuted
                                            font.pixelSize: 8
                                        }

                                        Rectangle {
                                            width: 24; height: 24; radius: 12
                                            color: delMemMouse.containsMouse ? (window.isDark ? "#3A1622" : "#FEE2E2") : "transparent"
                                            Text { anchors.centerIn: parent; text: "🗑"; font.pixelSize: 11 }
                                            MouseArea {
                                                id: delMemMouse
                                                anchors.fill: parent
                                                hoverEnabled: true
                                                cursorShape: Qt.PointingHandCursor
                                                onClicked: jarvisBackend.deleteLearnedMemory(modelData.id)
                                            }
                                        }
                                    }

                                    Text {
                                        Layout.fillWidth: true
                                        text: modelData.content || ""
                                        color: textPrimary
                                        font.pixelSize: 11
                                        wrapMode: Text.Wrap
                                    }
                                }
                            }
                        }
                    }
                }
            }

            // ========================================== TAB 1: APRENDIZADO COMPORTAMENTAL
            ColumnLayout {
                visible: memoryManagerModal.memoryTab === 1
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: 14

                Text {
                    text: "PERFIL E HÁBITOS ADAPTADOS AUTOMATICAMENTE"
                    color: cyan
                    font.pixelSize: 11
                    font.weight: Font.Bold
                    font.letterSpacing: 1.2
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 12

                    // Card 1: Horário
                    Rectangle {
                        Layout.fillWidth: true
                        implicitHeight: 110
                        radius: 12
                        color: window.isDark ? "#0A172B" : "#F8FAFC"
                        border.color: window.isDark ? "#173452" : "#E2E8F0"

                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 14
                            spacing: 4

                            Text { text: "🕒 HORÁRIO MAIS ATIVO"; color: textMuted; font.pixelSize: 9; font.letterSpacing: 1 }
                            Text {
                                text: jarvisBackend.behaviorProfile && jarvisBackend.behaviorProfile.horario_mais_ativo ? jarvisBackend.behaviorProfile.horario_mais_ativo.value : "Calculando padrões..."
                                color: textPrimary
                                font.pixelSize: 14
                                font.weight: Font.Bold
                            }
                            Text { text: "Detectado com base nos seus picos de atividade diários."; color: textMuted; font.pixelSize: 8; wrapMode: Text.Wrap; Layout.fillWidth: true }
                        }
                    }

                    // Card 2: Linguagem
                    Rectangle {
                        Layout.fillWidth: true
                        implicitHeight: 110
                        radius: 12
                        color: window.isDark ? "#0A172B" : "#F8FAFC"
                        border.color: window.isDark ? "#173452" : "#E2E8F0"

                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 14
                            spacing: 4

                            Text { text: "💻 LINGUAGEM PREDILETA"; color: cyan; font.pixelSize: 9; font.letterSpacing: 1 }
                            Text {
                                text: jarvisBackend.behaviorProfile && jarvisBackend.behaviorProfile.linguagem_predileta ? jarvisBackend.behaviorProfile.linguagem_predileta.value : "Detectando linguagem..."
                                color: textPrimary
                                font.pixelSize: 14
                                font.weight: Font.Bold
                            }
                            Text { text: "Prioriza exemplos e soluções na sua stack mais usada."; color: textMuted; font.pixelSize: 8; wrapMode: Text.Wrap; Layout.fillWidth: true }
                        }
                    }

                    // Card 3: Estilo
                    Rectangle {
                        Layout.fillWidth: true
                        implicitHeight: 110
                        radius: 12
                        color: window.isDark ? "#0A172B" : "#F8FAFC"
                        border.color: window.isDark ? "#173452" : "#E2E8F0"

                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 14
                            spacing: 4

                            Text { text: "📝 ESTILO DE RESPOSTA"; color: violet; font.pixelSize: 9; font.letterSpacing: 1 }
                            Text {
                                text: jarvisBackend.behaviorProfile && jarvisBackend.behaviorProfile.estilo_resposta ? jarvisBackend.behaviorProfile.estilo_resposta.value : "Adaptando ao seu ritmo..."
                                color: textPrimary
                                font.pixelSize: 14
                                font.weight: Font.Bold
                            }
                            Text { text: "Respostas moldadas dinamicamente ao seu nível de detalhamento preferido."; color: textMuted; font.pixelSize: 8; wrapMode: Text.Wrap; Layout.fillWidth: true }
                        }
                    }
                }

                Item { Layout.fillHeight: true }
            }
        }
    }

    Popup {
        id: confirmDialog
        parent: Overlay.overlay
        anchors.centerIn: parent
        width: Math.min(window.width - 160, 520)
        modal: true
        focus: true
        padding: 0
        closePolicy: Popup.NoAutoClose

        property string token: ""
        property string description: ""

        Overlay.modal: Rectangle { color: window.isDark ? "#DD020712" : "#80000000" }
        background: Rectangle { radius: 14; color: window.isDark ? "#0B1526" : "#FFFFFF"; border.color: window.isDark ? "#C9803A" : "#CBD5E1"; border.width: 1 }

        contentItem: ColumnLayout {
            anchors.fill: parent
            anchors.margins: 20
            spacing: 12

            Text { text: "CONFIRMAR AÇÃO"; color: "#F6C453"; font.pixelSize: 15; font.weight: Font.DemiBold; font.letterSpacing: 1.5 }
            Text {
                Layout.fillWidth: true
                text: "O " + (jarvisBackend.systemName || "Jarvis") + " quer executar:"
                color: textMuted; font.pixelSize: 10
            }
            Text {
                Layout.fillWidth: true
                text: confirmDialog.description
                color: textPrimary; font.pixelSize: 12; wrapMode: Text.Wrap
            }
            Text { text: "Só aprove se você tem certeza. Pode ser irreversível."; color: textMuted; font.pixelSize: 9 }

            RowLayout {
                Layout.fillWidth: true
                spacing: 10
                Item { Layout.fillWidth: true }
                JarvisButton {
                    variant: "secondary"
                    width: 120; height: 40
                    text: "✕  RECUSAR"
                    onClicked: {
                        jarvisBackend.resolveConfirmation(confirmDialog.token, false)
                        confirmDialog.close()
                    }
                }
                JarvisButton {
                    variant: "success"
                    width: 120; height: 40
                    text: "✔  APROVAR"
                    onClicked: {
                        jarvisBackend.resolveConfirmation(confirmDialog.token, true)
                        confirmDialog.close()
                    }
                }
            }
        }
    }

    // ===================================================== CONFIRMAÇÃO DE SAÍDA DO SISTEMA
    Popup {
        id: exitConfirmDialog
        objectName: "exitConfirmDialog"
        parent: Overlay.overlay
        anchors.centerIn: parent
        width: Math.min(window.width - 160, 500)
        implicitHeight: exitCol.implicitHeight + 48
        modal: true
        focus: true
        padding: 0
        closePolicy: Popup.CloseOnEscape

        property bool forceExit: false

        Overlay.modal: Rectangle { color: window.isDark ? "#DD020712" : "#80000000" }
        background: Rectangle {
            radius: 16
            color: window.isDark ? "#0B1526" : "#FFFFFF"
            border.color: window.isDark ? "#26516A" : "#CBD5E1"
            border.width: 1
        }

        contentItem: ColumnLayout {
            id: exitCol
            anchors.fill: parent
            anchors.margins: 24
            spacing: 14

            RowLayout {
                Layout.fillWidth: true
                spacing: 12
                Rectangle {
                    width: 42; height: 42; radius: 21
                    color: window.isDark ? "#3A1A22" : "#FEE2E2"
                    border.color: window.isDark ? "#5C202C" : "#FECACA"
                    Text { anchors.centerIn: parent; text: "⏻"; color: "#EF4444"; font.pixelSize: 20; font.weight: Font.Bold }
                }
                Column {
                    Layout.fillWidth: true
                    spacing: 2
                    Text {
                        text: "FECHAR O " + (jarvisBackend.systemName ? jarvisBackend.systemName.toUpperCase() : "JARVIS")
                        color: textPrimary
                        font.pixelSize: 15
                        font.weight: Font.DemiBold
                        font.letterSpacing: 1.5
                    }
                    Text {
                        text: "CONFIRMAÇÃO DE ENCERRAMENTO"
                        color: cyan
                        font.pixelSize: 8
                        font.weight: Font.DemiBold
                        font.letterSpacing: 1.2
                    }
                }
            }

            Rectangle { Layout.fillWidth: true; height: 1; color: window.isDark ? "#142840" : "#E2E8F0" }

            Text {
                Layout.fillWidth: true
                text: "Deseja realmente sair e fechar o aplicativo " + (jarvisBackend.systemName || "Jarvis") + "?"
                color: textPrimary
                font.pixelSize: 13
                font.weight: Font.Medium
            }

            Text {
                Layout.fillWidth: true
                text: "Todas as tarefas e conexões ativas serão finalizadas com segurança."
                color: textMuted
                font.pixelSize: 10
            }

            Item { Layout.fillWidth: true; Layout.preferredHeight: 6 }

            RowLayout {
                Layout.fillWidth: true
                spacing: 12
                Item { Layout.fillWidth: true }
                JarvisButton {
                    variant: "secondary"
                    implicitHeight: 38
                    implicitWidth: 120
                    Layout.preferredWidth: 120
                    Layout.preferredHeight: 38
                    text: "✕  CANCELAR"
                    onClicked: exitConfirmDialog.close()
                }
                JarvisButton {
                    variant: "danger"
                    implicitHeight: 38
                    implicitWidth: 130
                    Layout.preferredWidth: 130
                    Layout.preferredHeight: 38
                    text: "⏻  SIM, FECHAR"
                    onClicked: {
                        exitConfirmDialog.forceExit = true
                        exitConfirmDialog.close()
                        Qt.quit()
                    }
                }
            }
        }
    }

    // ===================================================== EDITOR DE ROTINA
    Popup {
        id: routineEditor
        objectName: "routineEditor"
        parent: Overlay.overlay
        anchors.centerIn: parent
        width: Math.min(window.width - 120, 640)
        height: Math.min(window.height - 80, 560)
        modal: true
        focus: true
        padding: 0
        closePolicy: Popup.CloseOnEscape

        property int routineId: 0

        function openNew() {
            routineId = 0
            reName.text = ""
            reDesc.text = ""
            reSteps.text = ""
            open()
        }
        function openEdit(routine) {
            routineId = routine.id
            reName.text = routine.name
            reDesc.text = routine.description
            reSteps.text = routine.steps
            open()
        }

        Overlay.modal: Rectangle { color: window.isDark ? "#CC020712" : "#80000000" }
        background: Rectangle { radius: 16; color: window.isDark ? "#081122" : "#FFFFFF"; border.color: window.isDark ? "#26516A" : "#CBD5E1"; border.width: 1 }

        contentItem: ColumnLayout {
            anchors.fill: parent
            anchors.margins: 22
            spacing: 12

            Text {
                text: routineEditor.routineId > 0 ? "EDITAR ROTINA" : "NOVA ROTINA"
                color: textPrimary
                font.pixelSize: 16
                font.weight: Font.DemiBold
                font.letterSpacing: 2
            }

            Text { text: "NOME"; color: textMuted; font.pixelSize: 8; font.letterSpacing: 1.1 }
            TextField {
                id: reName
                Layout.fillWidth: true
                Layout.preferredHeight: 40
                placeholderText: "Ex.: Modo trabalho"
                placeholderTextColor: window.isDark ? "#526D83" : "#94A3B8"
                color: textPrimary
                selectByMouse: true
                font.pixelSize: 12
                leftPadding: 12
                background: Rectangle { radius: 9; color: window.isDark ? "#0D1D33" : "#FFFFFF"; border.color: parent.activeFocus ? cyan : (window.isDark ? "#23435E" : "#CBD5E1") }
            }

            Text { text: "DESCRIÇÃO (opcional)"; color: textMuted; font.pixelSize: 8; font.letterSpacing: 1.1 }
            TextField {
                id: reDesc
                Layout.fillWidth: true
                Layout.preferredHeight: 40
                placeholderText: "Uma linha sobre o que ela faz"
                placeholderTextColor: window.isDark ? "#526D83" : "#94A3B8"
                color: textPrimary
                selectByMouse: true
                font.pixelSize: 12
                leftPadding: 12
                background: Rectangle { radius: 9; color: window.isDark ? "#0D1D33" : "#FFFFFF"; border.color: parent.activeFocus ? cyan : (window.isDark ? "#23435E" : "#CBD5E1") }
            }

            Text { text: "PASSOS — um por linha, em linguagem natural"; color: textMuted; font.pixelSize: 8; font.letterSpacing: 1.1 }
            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                radius: 9
                color: window.isDark ? "#0D1D33" : "#FFFFFF"
                border.color: reSteps.activeFocus ? cyan : (window.isDark ? "#23435E" : "#CBD5E1")
                ScrollView {
                    anchors.fill: parent
                    anchors.margins: 8
                    TextArea {
                        id: reSteps
                        color: textPrimary
                        font.pixelSize: 12
                        wrapMode: TextArea.Wrap
                        placeholderText: "Abra o YouTube e pesquise por 'lofi hip hop radio'\nAbra a pasta de Downloads"
                        placeholderTextColor: window.isDark ? "#526D83" : "#94A3B8"
                        background: null
                    }
                }
            }

            RowLayout {
                Layout.fillWidth: true
                Text {
                    Layout.fillWidth: true
                    text: "Cada passo vira um comando para o agente, em ordem."
                    color: textMuted
                    font.pixelSize: 9
                }
                JarvisButton {
                    variant: "secondary"
                    width: 110; height: 40; text: "✕  CANCELAR"
                    onClicked: routineEditor.close()
                }
                JarvisButton {
                    variant: "save"
                    width: 150; height: 40; text: "✔  SALVAR"
                    enabled: reName.text.trim().length > 0 && reSteps.text.trim().length > 0
                    onClicked: {
                        jarvisBackend.saveRoutine(routineEditor.routineId, reName.text, reDesc.text, reSteps.text)
                        routineEditor.close()
                    }
                }
            }
        }
    }

    Popup {
        id: routineDelete
        parent: Overlay.overlay
        anchors.centerIn: parent
        width: Math.min(window.width - 200, 460)
        modal: true
        focus: true
        padding: 0
        closePolicy: Popup.CloseOnEscape

        property var pending: null

        Overlay.modal: Rectangle { color: window.isDark ? "#DD020712" : "#80000000" }
        background: Rectangle { radius: 14; color: window.isDark ? "#0B1526" : "#FFFFFF"; border.color: window.isDark ? "#C9803A" : "#CBD5E1"; border.width: 1 }

        contentItem: ColumnLayout {
            anchors.fill: parent
            anchors.margins: 20
            spacing: 12
            Text { text: "REMOVER ROTINA"; color: "#F6C453"; font.pixelSize: 14; font.weight: Font.DemiBold; font.letterSpacing: 1.4 }
            Text {
                Layout.fillWidth: true
                text: routineDelete.pending ? ("Apagar a rotina \"" + routineDelete.pending.name + "\"? Não dá pra desfazer.") : ""
                color: textPrimary; font.pixelSize: 12; wrapMode: Text.Wrap
            }
            RowLayout {
                Layout.fillWidth: true
                Item { Layout.fillWidth: true }
                JarvisButton {
                    variant: "secondary"
                    width: 110; height: 38; text: "✕  CANCELAR"
                    onClicked: routineDelete.close()
                }
                JarvisButton {
                    variant: "danger"
                    width: 110; height: 38; text: "🗑  APAGAR"
                    onClicked: {
                        if (routineDelete.pending)
                            jarvisBackend.deleteRoutine(routineDelete.pending.id)
                        routineDelete.close()
                    }
                }
            }
        }
    }

    // ===================================================== TESTE DA WEBCAM
    Popup {
        id: webcamTest
        objectName: "webcamTest"
        parent: Overlay.overlay
        anchors.centerIn: parent
        width: Math.min(window.width - 160, 560)
        height: Math.min(window.height - 120, 560)
        modal: true
        focus: true
        padding: 0
        closePolicy: Popup.CloseOnEscape

        property string imageUri: ""
        property string result: ""
        property bool loading: true
        function reset() { imageUri = ""; result = ""; loading = true }

        Overlay.modal: Rectangle { color: window.isDark ? "#CC020712" : "#80000000" }
        background: Rectangle { radius: 15; color: window.isDark ? "#0A1526" : "#FFFFFF"; border.color: window.isDark ? "#26516A" : "#CBD5E1"; border.width: 1 }

        contentItem: ColumnLayout {
            anchors.fill: parent
            anchors.margins: 20
            spacing: 12

            RowLayout {
                Layout.fillWidth: true
                Text { text: "TESTE DA WEBCAM"; color: cyan; font.pixelSize: 14; font.weight: Font.DemiBold; font.letterSpacing: 1.4; Layout.fillWidth: true }
                JarvisButton {
                    variant: "close"
                    Layout.preferredWidth: 32
                    Layout.preferredHeight: 32
                    Layout.alignment: Qt.AlignVCenter
                    text: "✕"
                    textSize: 12
                    onClicked: webcamTest.close()
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                radius: 10
                color: window.isDark ? "#060C1A" : "#F8FAFC"
                border.color: window.isDark ? "#1B355A" : "#CBD5E1"
                Image {
                    anchors.fill: parent
                    anchors.margins: 8
                    source: webcamTest.imageUri
                    fillMode: Image.PreserveAspectFit
                    visible: webcamTest.imageUri.length > 0
                }
                Text {
                    anchors.centerIn: parent
                    visible: webcamTest.imageUri.length === 0
                    text: webcamTest.loading ? "Capturando pela webcam..." : "Sem imagem."
                    color: textMuted; font.pixelSize: 11
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 90
                radius: 10
                color: window.isDark ? "#0A1730" : "#F8FAFC"
                border.color: window.isDark ? "#1B355A" : "#CBD5E1"
                ScrollView {
                    anchors.fill: parent
                    anchors.margins: 10
                    clip: true
                    Text {
                        width: webcamTest.width - 60
                        text: webcamTest.loading ? "Perguntando pra IA o que ela vê..." : (webcamTest.result || "")
                        color: webcamTest.loading ? cyan : textPrimary
                        font.pixelSize: 10
                        wrapMode: Text.Wrap
                    }
                }
            }
        }
    }

    // =================================================== CONFIRMAÇÃO GENÉRICA (Sistema)
    Popup {
        id: sysConfirm
        parent: Overlay.overlay
        anchors.centerIn: parent
        width: Math.min(window.width - 180, 480)
        modal: true
        focus: true
        padding: 0
        closePolicy: Popup.NoAutoClose

        property var cb: null
        property string msg: ""
        function open2(message, callback) { msg = message; cb = callback; open() }

        Overlay.modal: Rectangle { color: window.isDark ? "#DD020712" : "#80000000" }
        background: Rectangle { radius: 14; color: window.isDark ? "#0B1526" : "#FFFFFF"; border.color: window.isDark ? "#C9803A" : "#CBD5E1"; border.width: 1 }

        contentItem: ColumnLayout {
            anchors.fill: parent
            anchors.margins: 20
            spacing: 14
            Text { text: "CONFIRMAR"; color: "#F6C453"; font.pixelSize: 14; font.weight: Font.DemiBold; font.letterSpacing: 1.4 }
            Text { Layout.fillWidth: true; text: sysConfirm.msg; color: textPrimary; font.pixelSize: 12; wrapMode: Text.Wrap }
            RowLayout {
                Layout.fillWidth: true
                Item { Layout.fillWidth: true }
                JarvisButton {
                    variant: "secondary"
                    width: 110; height: 38; text: "✕  CANCELAR"
                    onClicked: sysConfirm.close()
                }
                JarvisButton {
                    variant: "danger"
                    width: 120; height: 38; text: "✔  CONFIRMAR"
                    onClicked: { var f = sysConfirm.cb; sysConfirm.close(); if (f) f() }
                }
            }
        }
    }

    // =================================================== EDITOR DE AGENDAMENTO
    Popup {
        id: scheduleEditor
        objectName: "scheduleEditor"
        parent: Overlay.overlay
        anchors.centerIn: parent
        width: Math.min(window.width - 160, 520)
        height: 340
        modal: true
        focus: true
        padding: 0
        closePolicy: Popup.CloseOnEscape

        property int routineId: 0
        property string routineName: ""
        readonly property var kinds: [
            {"label": "Uma vez", "value": "once"},
            {"label": "Todo dia", "value": "daily"},
            {"label": "Toda semana", "value": "weekly"}
        ]

        function openFor(routine) {
            routineId = routine.id
            routineName = routine.name
            seKind.currentIndex = routine.scheduleKind === "daily" ? 1
                                  : routine.scheduleKind === "weekly" ? 2 : 0
            seDate.text = ""
            seTime.text = ""
            seWeekday.currentIndex = 0
            open()
        }

        Overlay.modal: Rectangle { color: window.isDark ? "#CC020712" : "#80000000" }
        background: Rectangle { radius: 15; color: window.isDark ? "#081122" : "#FFFFFF"; border.color: window.isDark ? "#26516A" : "#CBD5E1"; border.width: 1 }

        contentItem: ColumnLayout {
            anchors.fill: parent
            anchors.margins: 22
            spacing: 12

            Text {
                text: "AGENDAR  //  " + scheduleEditor.routineName.toUpperCase()
                color: textPrimary
                font.pixelSize: 15
                font.weight: Font.DemiBold
                font.letterSpacing: 1.6
                elide: Text.ElideRight
                Layout.fillWidth: true
            }
            Text {
                text: "O Jarvis roda a rotina neste horário enquanto o app estiver aberto."
                color: textMuted
                font.pixelSize: 9
                Layout.fillWidth: true
                wrapMode: Text.Wrap
            }

            Text { text: "QUANDO"; color: textMuted; font.pixelSize: 8; font.letterSpacing: 1.1 }
            FuturisticCombo {
                id: seKind
                Layout.fillWidth: true
                Layout.preferredHeight: 40
                textRole: "label"
                model: scheduleEditor.kinds
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 12

                ColumnLayout {
                    visible: seKind.currentIndex === 0
                    spacing: 5
                    Text { text: "DATA (DD/MM/AAAA)"; color: textMuted; font.pixelSize: 8; font.letterSpacing: 1.1 }
                    TextField {
                        id: seDate
                        Layout.preferredWidth: 150
                        Layout.preferredHeight: 40
                        inputMask: "99/99/9999;_"
                        placeholderText: "31/08/2026"
                        placeholderTextColor: window.isDark ? "#526D83" : "#94A3B8"
                        color: textPrimary
                        font.pixelSize: 12
                        leftPadding: 12
                        background: Rectangle { radius: 9; color: window.isDark ? "#0D1D33" : "#FFFFFF"; border.color: parent.activeFocus ? cyan : (window.isDark ? "#23435E" : "#CBD5E1") }
                    }
                }

                ColumnLayout {
                    visible: seKind.currentIndex === 2
                    spacing: 5
                    Text { text: "DIA DA SEMANA"; color: textMuted; font.pixelSize: 8; font.letterSpacing: 1.1 }
                    FuturisticCombo {
                        id: seWeekday
                        Layout.preferredWidth: 160
                        Layout.preferredHeight: 40
                        model: ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]
                    }
                }

                ColumnLayout {
                    spacing: 5
                    Text { text: "HORA (HH:MM)"; color: textMuted; font.pixelSize: 8; font.letterSpacing: 1.1 }
                    TextField {
                        id: seTime
                        Layout.preferredWidth: 110
                        Layout.preferredHeight: 40
                        inputMask: "99:99;_"
                        placeholderText: "08:00"
                        placeholderTextColor: window.isDark ? "#526D83" : "#94A3B8"
                        color: textPrimary
                        font.pixelSize: 12
                        leftPadding: 12
                        background: Rectangle { radius: 9; color: window.isDark ? "#0D1D33" : "#FFFFFF"; border.color: parent.activeFocus ? cyan : (window.isDark ? "#23435E" : "#CBD5E1") }
                    }
                }
                Item { Layout.fillWidth: true }
            }

            RowLayout {
                Layout.fillWidth: true
                Layout.topMargin: 4
                Item { Layout.fillWidth: true }
                JarvisButton {
                    variant: "secondary"
                    width: 110; height: 40; text: "✕  CANCELAR"
                    onClicked: scheduleEditor.close()
                }
                JarvisButton {
                    variant: "save"
                    width: 160; height: 40; text: "⏰  SALVAR AGENDAMENTO"
                    textSize: 9
                    onClicked: {
                        jarvisBackend.setSchedule(
                            scheduleEditor.routineId,
                            scheduleEditor.kinds[seKind.currentIndex].value,
                            seDate.text,
                            seTime.text,
                            seKind.currentIndex === 2 ? seWeekday.currentIndex : -1
                        )
                        scheduleEditor.close()
                    }
                }
            }
        }
    }

    // =================================================== EDITOR DE COMPROMISSO
    Popup {
        id: appointmentEditor
        objectName: "appointmentEditor"
        parent: Overlay.overlay
        anchors.centerIn: parent
        width: Math.min(window.width - 140, 560)
        height: 470
        modal: true
        focus: true
        padding: 0
        closePolicy: Popup.CloseOnEscape

        property int apptId: 0
        property var contactOptions: [{"id": 0, "name": "— sem contato —"}].concat(jarvisBackend.contacts)

        function reminderIndexFor(minutes) {
            var choices = jarvisBackend.reminderChoices
            for (var i = 0; i < choices.length; i++)
                if (choices[i].value === minutes) return i
            return 0
        }
        function contactIndexFor(id) {
            for (var i = 0; i < contactOptions.length; i++)
                if (contactOptions[i].id === id) return i
            return 0
        }
        function openNew() {
            apptId = 0
            contactOptions = [{"id": 0, "name": "— sem contato —"}].concat(jarvisBackend.contacts)
            aeTitle.text = ""; aeDate.text = ""; aeTime.text = ""
            aeLocation.text = ""; aeNotes.text = ""
            aeContact.currentIndex = 0
            aeReminder.currentIndex = reminderIndexFor(15)
            open()
        }
        function openEdit(appt) {
            apptId = appt.id
            contactOptions = [{"id": 0, "name": "— sem contato —"}].concat(jarvisBackend.contacts)
            aeTitle.text = appt.title
            aeDate.text = appt.dateText
            aeTime.text = appt.timeText
            aeLocation.text = appt.location
            aeNotes.text = appt.notes
            aeContact.currentIndex = contactIndexFor(appt.contactId)
            aeReminder.currentIndex = reminderIndexFor(appt.reminderMinutes)
            open()
        }

        Overlay.modal: Rectangle { color: window.isDark ? "#CC020712" : "#80000000" }
        background: Rectangle { radius: 15; color: window.isDark ? "#081122" : "#FFFFFF"; border.color: window.isDark ? "#26516A" : "#CBD5E1"; border.width: 1 }

        contentItem: ColumnLayout {
            anchors.fill: parent
            anchors.margins: 22
            spacing: 11

            Text {
                text: appointmentEditor.apptId > 0 ? "EDITAR COMPROMISSO" : "NOVO COMPROMISSO"
                color: textPrimary; font.pixelSize: 15; font.weight: Font.DemiBold; font.letterSpacing: 1.6
            }

            Text { text: "TÍTULO"; color: textMuted; font.pixelSize: 8; font.letterSpacing: 1.1 }
            TextField {
                id: aeTitle
                Layout.fillWidth: true; Layout.preferredHeight: 38
                placeholderText: "Ex.: Reunião com o João"
                placeholderTextColor: window.isDark ? "#526D83" : "#94A3B8"; color: textPrimary; font.pixelSize: 12; leftPadding: 12
                background: Rectangle { radius: 9; color: window.isDark ? "#0D1D33" : "#FFFFFF"; border.color: parent.activeFocus ? cyan : (window.isDark ? "#23435E" : "#CBD5E1") }
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 12
                ColumnLayout {
                    spacing: 5
                    Text { text: "DATA (DD/MM/AAAA)"; color: textMuted; font.pixelSize: 8; font.letterSpacing: 1.1 }
                    TextField {
                        id: aeDate
                        Layout.preferredWidth: 160; Layout.preferredHeight: 38
                        inputMask: "99/99/9999;_"
                        placeholderText: "31/08/2026"; placeholderTextColor: window.isDark ? "#526D83" : "#94A3B8"; color: textPrimary; font.pixelSize: 12; leftPadding: 12
                        background: Rectangle { radius: 9; color: window.isDark ? "#0D1D33" : "#FFFFFF"; border.color: parent.activeFocus ? cyan : (window.isDark ? "#23435E" : "#CBD5E1") }
                    }
                }
                ColumnLayout {
                    spacing: 5
                    Text { text: "HORA (HH:MM)"; color: textMuted; font.pixelSize: 8; font.letterSpacing: 1.1 }
                    TextField {
                        id: aeTime
                        Layout.preferredWidth: 110; Layout.preferredHeight: 38
                        inputMask: "99:99;_"
                        placeholderText: "15:00"; placeholderTextColor: window.isDark ? "#526D83" : "#94A3B8"; color: textPrimary; font.pixelSize: 12; leftPadding: 12
                        background: Rectangle { radius: 9; color: window.isDark ? "#0D1D33" : "#FFFFFF"; border.color: parent.activeFocus ? cyan : (window.isDark ? "#23435E" : "#CBD5E1") }
                    }
                }
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 5
                    Text { text: "LEMBRETE"; color: textMuted; font.pixelSize: 8; font.letterSpacing: 1.1 }
                    FuturisticCombo {
                        id: aeReminder
                        Layout.fillWidth: true; Layout.preferredHeight: 38
                        textRole: "label"
                        model: jarvisBackend.reminderChoices
                    }
                }
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 12
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 5
                    Text { text: "LOCAL (opcional)"; color: textMuted; font.pixelSize: 8; font.letterSpacing: 1.1 }
                    TextField {
                        id: aeLocation
                        Layout.fillWidth: true; Layout.preferredHeight: 38
                        placeholderText: "Sala 3 / Google Meet / ..."
                        placeholderTextColor: window.isDark ? "#526D83" : "#94A3B8"; color: textPrimary; font.pixelSize: 12; leftPadding: 12
                        background: Rectangle { radius: 9; color: window.isDark ? "#0D1D33" : "#FFFFFF"; border.color: parent.activeFocus ? cyan : (window.isDark ? "#23435E" : "#CBD5E1") }
                    }
                }
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 5
                    Text { text: "CONTATO (opcional)"; color: textMuted; font.pixelSize: 8; font.letterSpacing: 1.1 }
                    FuturisticCombo {
                        id: aeContact
                        Layout.fillWidth: true; Layout.preferredHeight: 38
                        textRole: "name"
                        model: appointmentEditor.contactOptions
                    }
                }
            }

            Text { text: "NOTAS (opcional)"; color: textMuted; font.pixelSize: 8; font.letterSpacing: 1.1 }
            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                radius: 9
                color: window.isDark ? "#0D1D33" : "#FFFFFF"
                border.color: aeNotes.activeFocus ? cyan : (window.isDark ? "#23435E" : "#CBD5E1")
                ScrollView {
                    anchors.fill: parent
                    anchors.margins: 8
                    TextArea { id: aeNotes; color: textPrimary; font.pixelSize: 11; wrapMode: TextArea.Wrap; background: null }
                }
            }

            RowLayout {
                Layout.fillWidth: true
                Item { Layout.fillWidth: true }
                JarvisButton {
                    variant: "secondary"
                    width: 110; height: 40; text: "✕  CANCELAR"
                    onClicked: appointmentEditor.close()
                }
                JarvisButton {
                    variant: "save"
                    width: 150; height: 40; text: "✔  SALVAR"
                    enabled: aeTitle.text.trim().length > 0
                    onClicked: {
                        jarvisBackend.saveAppointment(
                            appointmentEditor.apptId, aeTitle.text, aeDate.text, aeTime.text,
                            aeLocation.text, aeNotes.text,
                            appointmentEditor.contactOptions[aeContact.currentIndex].id,
                            jarvisBackend.reminderChoices[aeReminder.currentIndex].value
                        )
                        appointmentEditor.close()
                    }
                }
            }
        }
    }

    // ===================================================== EDITOR DE CONTATO
    Popup {
        id: contactEditor
        objectName: "contactEditor"
        parent: Overlay.overlay
        anchors.centerIn: parent
        width: Math.min(window.width - 160, 500)
        height: 430
        modal: true
        focus: true
        padding: 0
        closePolicy: Popup.CloseOnEscape

        property int contactId: 0

        function openNew() {
            contactId = 0
            ceName.text = ""; cePhone.text = ""; ceEmail.text = ""; ceBday.text = ""; ceNotes.text = ""
            open()
        }
        function openEdit(contact) {
            contactId = contact.id
            ceName.text = contact.name
            cePhone.text = contact.phone
            ceEmail.text = contact.email
            ceBday.text = contact.birthday
            ceNotes.text = contact.notes
            open()
        }

        Overlay.modal: Rectangle { color: window.isDark ? "#CC020712" : "#80000000" }
        background: Rectangle { radius: 15; color: window.isDark ? "#081122" : "#FFFFFF"; border.color: window.isDark ? "#26516A" : "#CBD5E1"; border.width: 1 }

        contentItem: ColumnLayout {
            anchors.fill: parent
            anchors.margins: 22
            spacing: 11

            Text {
                text: contactEditor.contactId > 0 ? "EDITAR CONTATO" : "NOVO CONTATO"
                color: textPrimary; font.pixelSize: 15; font.weight: Font.DemiBold; font.letterSpacing: 1.6
            }

            Text { text: "NOME"; color: textMuted; font.pixelSize: 8; font.letterSpacing: 1.1 }
            TextField {
                id: ceName
                Layout.fillWidth: true; Layout.preferredHeight: 38
                placeholderText: "Ex.: Maria Silva"
                placeholderTextColor: window.isDark ? "#526D83" : "#94A3B8"; color: textPrimary; font.pixelSize: 12; leftPadding: 12
                background: Rectangle { radius: 9; color: window.isDark ? "#0D1D33" : "#FFFFFF"; border.color: parent.activeFocus ? cyan : (window.isDark ? "#23435E" : "#CBD5E1") }
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 12
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 5
                    Text { text: "TELEFONE"; color: textMuted; font.pixelSize: 8; font.letterSpacing: 1.1 }
                    TextField {
                        id: cePhone
                        Layout.fillWidth: true; Layout.preferredHeight: 38
                        placeholderText: "11 91234-5678"
                        placeholderTextColor: window.isDark ? "#526D83" : "#94A3B8"; color: textPrimary; font.pixelSize: 12; leftPadding: 12
                        background: Rectangle { radius: 9; color: window.isDark ? "#0D1D33" : "#FFFFFF"; border.color: parent.activeFocus ? cyan : (window.isDark ? "#23435E" : "#CBD5E1") }
                    }
                }
                ColumnLayout {
                    spacing: 5
                    Text { text: "ANIVERSÁRIO (DD/MM)"; color: textMuted; font.pixelSize: 8; font.letterSpacing: 1.1 }
                    TextField {
                        id: ceBday
                        Layout.preferredWidth: 150; Layout.preferredHeight: 38
                        placeholderText: "14/03 ou 14/03/1990"
                        placeholderTextColor: window.isDark ? "#526D83" : "#94A3B8"; color: textPrimary; font.pixelSize: 12; leftPadding: 12
                        background: Rectangle { radius: 9; color: window.isDark ? "#0D1D33" : "#FFFFFF"; border.color: parent.activeFocus ? cyan : (window.isDark ? "#23435E" : "#CBD5E1") }
                    }
                }
            }

            Text { text: "E-MAIL"; color: textMuted; font.pixelSize: 8; font.letterSpacing: 1.1 }
            TextField {
                id: ceEmail
                Layout.fillWidth: true; Layout.preferredHeight: 38
                placeholderText: "maria@exemplo.com"
                placeholderTextColor: window.isDark ? "#526D83" : "#94A3B8"; color: textPrimary; font.pixelSize: 12; leftPadding: 12
                background: Rectangle { radius: 9; color: window.isDark ? "#0D1D33" : "#FFFFFF"; border.color: parent.activeFocus ? cyan : (window.isDark ? "#23435E" : "#CBD5E1") }
            }

            Text { text: "NOTAS (opcional)"; color: textMuted; font.pixelSize: 8; font.letterSpacing: 1.1 }
            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                radius: 9
                color: window.isDark ? "#0D1D33" : "#FFFFFF"
                border.color: ceNotes.activeFocus ? cyan : (window.isDark ? "#23435E" : "#CBD5E1")
                ScrollView {
                    anchors.fill: parent
                    anchors.margins: 8
                    TextArea { id: ceNotes; color: textPrimary; font.pixelSize: 11; wrapMode: TextArea.Wrap; background: null }
                }
            }

            RowLayout {
                Layout.fillWidth: true
                Item { Layout.fillWidth: true }
                JarvisButton {
                    variant: "secondary"
                    width: 110; height: 40; text: "✕  CANCELAR"
                    onClicked: contactEditor.close()
                }
                JarvisButton {
                    variant: "save"
                    width: 150; height: 40; text: "✔  SALVAR"
                    enabled: ceName.text.trim().length > 0
                    onClicked: {
                        jarvisBackend.saveContact(
                            contactEditor.contactId, ceName.text, cePhone.text,
                            ceEmail.text, ceBday.text, ceNotes.text
                        )
                        contactEditor.close()
                    }
                }
            }
        }
    }

    Popup {
        id: agendaDelete
        parent: Overlay.overlay
        anchors.centerIn: parent
        width: Math.min(window.width - 200, 460)
        modal: true
        focus: true
        padding: 0
        closePolicy: Popup.CloseOnEscape

        property string kind: ""
        property var pending: null

        Overlay.modal: Rectangle { color: window.isDark ? "#DD020712" : "#80000000" }
        background: Rectangle { radius: 14; color: window.isDark ? "#0B1526" : "#FFFFFF"; border.color: window.isDark ? "#C9803A" : "#CBD5E1"; border.width: 1 }

        contentItem: ColumnLayout {
            anchors.fill: parent
            anchors.margins: 20
            spacing: 12
            Text { text: agendaDelete.kind === "contact" ? "REMOVER CONTATO" : "REMOVER COMPROMISSO"; color: "#F6C453"; font.pixelSize: 14; font.weight: Font.DemiBold; font.letterSpacing: 1.4 }
            Text {
                Layout.fillWidth: true
                text: agendaDelete.pending
                      ? ("Apagar \"" + (agendaDelete.kind === "contact" ? agendaDelete.pending.name : agendaDelete.pending.title) + "\"?")
                      : ""
                color: textPrimary; font.pixelSize: 12; wrapMode: Text.Wrap
            }
            RowLayout {
                Layout.fillWidth: true
                Item { Layout.fillWidth: true }
                JarvisButton {
                    variant: "secondary"
                    width: 110; height: 38; text: "✕  CANCELAR"
                    onClicked: agendaDelete.close()
                }
                JarvisButton {
                    variant: "danger"
                    width: 110; height: 38; text: "🗑  APAGAR"
                    onClicked: {
                        if (agendaDelete.pending) {
                            if (agendaDelete.kind === "contact")
                                jarvisBackend.deleteContact(agendaDelete.pending.id)
                            else
                                jarvisBackend.deleteAppointment(agendaDelete.pending.id)
                        }
                        agendaDelete.close()
                    }
                }
            }
        }
    }

    function urlToPath(u) {
        var s = decodeURIComponent(u.toString())
        s = s.replace(/^file:\/{2,3}/, "")
        if (/^\/[A-Za-z]:/.test(s)) s = s.substring(1)
        return s
    }
    function baseName(p) {
        if (!p) return ""
        var parts = p.split(/[\\/]/)
        return parts[parts.length - 1]
    }

    FileDialog {
        id: sharedFileDialog
        property var target: null
        property bool multi: false
        fileMode: multi ? FileDialog.OpenFiles : FileDialog.OpenFile
        onAccepted: {
            if (!target) return
            if (multi) {
                var arr = []
                for (var i = 0; i < selectedFiles.length; i++)
                    arr.push(window.urlToPath(selectedFiles[i]))
                if (target.addPaths && typeof target.addPaths === "function") {
                    target.addPaths(arr)
                } else {
                    target.paths = arr
                }
            } else {
                target.path = window.urlToPath(selectedFile)
            }
        }
    }

    FileDialog {
        id: attachmentDialog
        title: "Anexar ao chat"
        fileMode: FileDialog.OpenFiles
        nameFilters: [
            "Imagens e documentos (*.png *.jpg *.jpeg *.webp *.bmp *.gif *.tif *.tiff *.pdf *.docx *.xlsx *.xlsm *.txt *.md *.csv *.tsv *.json *.xml *.yaml *.yml *.log *.rst *.ini)",
            "Imagens (*.png *.jpg *.jpeg *.webp *.bmp *.gif *.tif *.tiff)",
            "Documentos (*.pdf *.docx *.xlsx *.xlsm *.txt *.md *.csv *.tsv *.json *.xml *.yaml *.yml *.log *.rst *.ini)",
            "Todos os arquivos (*)"
        ]
        onAccepted: {
            var arr = []
            for (var i = 0; i < selectedFiles.length; i++)
                arr.push(window.urlToPath(selectedFiles[i]))
            if (arr.length > 0)
                jarvisBackend.addAttachments(arr)
        }
    }

    FileDialog {
        id: keyFileDialog
        title: "Escolher a chave privada SSH"
        onAccepted: seKey.text = window.urlToPath(selectedFile)
    }

    FileDialog {
        id: pdfEditorFileDialog
        title: "Escolher arquivo PDF para editar"
        nameFilters: ["Arquivos PDF (*.pdf)", "Todos os arquivos (*)"]
        onAccepted: {
            var path = window.urlToPath(selectedFile)
            if (path) pdfEditorDialog.openFor(path)
        }
    }

    FileDialog {
        id: pdfImageFileDialog
        title: "Escolher imagem ou assinatura para inserir no PDF"
        nameFilters: ["Imagens (*.png *.jpg *.jpeg *.webp *.bmp)", "Todos os arquivos (*)"]
        onAccepted: {
            var path = window.urlToPath(selectedFile)
            if (path) pdfEditorDialog.selectedImagePath = path
        }
    }

    // ============================================== FERRAMENTAS DE SEGURANÇA
    Popup {
        id: securityPanel
        objectName: "securityPanel"
        parent: Overlay.overlay
        anchors.centerIn: parent

        readonly property int cols: width > 560 ? 3 : 2
        readonly property int gridRows: Math.ceil(
            jarvisBackend.securityActions.length / cols)

        width: Math.min(window.width - 100, 660)
        height: selected
                ? Math.min(window.height - 60,
                           176 + secFormRepeater.count * 66
                           + (secFormRepeater.count === 0 ? 34 : 0))
                : Math.min(window.height - 60, 108 + gridRows * 58)
        modal: true
        focus: true
        padding: 0
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

        property var selected: null

        function pick(action) { selected = action }
        function back() { selected = null }
        function submit() {
            if (!selected) return
            var params = {}
            for (var i = 0; i < secFormRepeater.count; i++) {
                var it = secFormRepeater.itemAt(i)
                if (it) params[it.fieldKey] = it.fieldValue
            }
            jarvisBackend.runSecurityAction(selected.id, params)
            selected = null
            securityPanel.close()
        }

        onOpened: selected = null

        Overlay.modal: Rectangle { color: window.isDark ? "#CC020712" : "#80000000" }
        background: Rectangle { radius: 15; color: window.isDark ? "#081122" : "#FFFFFF"; border.color: window.isDark ? "#26516A" : "#CBD5E1"; border.width: 1 }

        contentItem: ColumnLayout {
            anchors.fill: parent
            anchors.margins: 18
            spacing: 10

            RowLayout {
                Layout.fillWidth: true
                JarvisButton {
                    variant: "secondary"
                    visible: securityPanel.selected !== null
                    text: "‹  VOLTAR"
                    implicitHeight: 30; leftPadding: 8; rightPadding: 8; textSize: 9
                    onClicked: securityPanel.back()
                }
                Text {
                    Layout.fillWidth: true
                    text: securityPanel.selected
                          ? (securityPanel.selected.icon + "  " + securityPanel.selected.label.toUpperCase())
                          : "🛡  FERRAMENTAS DE SEGURANÇA"
                    color: textPrimary; font.pixelSize: 14; font.weight: Font.DemiBold; font.letterSpacing: 1.2
                    elide: Text.ElideRight
                }
                JarvisButton {
                    variant: "close"
                    Layout.preferredWidth: 32
                    Layout.preferredHeight: 32
                    Layout.alignment: Qt.AlignVCenter
                    text: "✕"
                    textSize: 12
                    onClicked: securityPanel.close()
                }
            }

            Text {
                Layout.fillWidth: true
                visible: securityPanel.selected === null
                text: "Só para testes autorizados nos seus próprios ativos. Ao clicar, o Jarvis pede os dados e roda a partir do seu PC — nada intrusivo."
                color: textMuted; font.pixelSize: 9; wrapMode: Text.Wrap
            }

            // ----- grade de acoes (sem scroll: cabe tudo)
            GridLayout {
                visible: securityPanel.selected === null
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.alignment: Qt.AlignTop
                columns: securityPanel.cols
                columnSpacing: 8
                rowSpacing: 8

                Repeater {
                    model: jarvisBackend.securityActions
                    delegate: Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 54
                        radius: 9
                        color: saMouse.containsMouse ? (window.isDark ? "#123247" : "#E0F2FE") : (window.isDark ? "#0B1B2E" : "#F8FAFC")
                        border.color: saMouse.containsMouse ? cyan : (window.isDark ? "#1F3B57" : "#CBD5E1")
                        Column {
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.verticalCenter: parent.verticalCenter
                            anchors.leftMargin: 9
                            anchors.rightMargin: 9
                            spacing: 1
                            Text {
                                text: modelData.icon + "  " + modelData.label
                                color: textPrimary; font.pixelSize: 10; font.weight: Font.DemiBold
                                elide: Text.ElideRight; width: parent.width
                            }
                            Text {
                                text: modelData.description
                                color: textMuted; font.pixelSize: 8
                                elide: Text.ElideRight; width: parent.width
                            }
                        }
                        MouseArea {
                            id: saMouse
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: securityPanel.pick(modelData)
                        }
                    }
                }
            }

            // ----- formulario da acao escolhida
            ColumnLayout {
                visible: securityPanel.selected !== null
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: 10

                Text {
                    Layout.fillWidth: true
                    text: securityPanel.selected ? securityPanel.selected.description : ""
                    color: textMuted; font.pixelSize: 10; wrapMode: Text.Wrap
                }

                Repeater {
                    id: secFormRepeater
                    model: securityPanel.selected ? securityPanel.selected.fields : []
                    delegate: ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 4
                        property string fieldKey: modelData.key
                        property alias fieldValue: saField.text
                        Text {
                            text: modelData.label + (modelData.optional ? "  (opcional)" : "")
                            color: textMuted; font.pixelSize: 8; font.letterSpacing: 1
                        }
                        TextField {
                            id: saField
                            Layout.fillWidth: true; Layout.preferredHeight: 38
                            text: modelData.default || ""
                            placeholderText: modelData.placeholder
                            placeholderTextColor: window.isDark ? "#526D83" : "#94A3B8"; color: textPrimary; font.pixelSize: 12; leftPadding: 12
                            background: Rectangle { radius: 9; color: window.isDark ? "#0D1D33" : "#FFFFFF"; border.color: parent.activeFocus ? cyan : (window.isDark ? "#23435E" : "#CBD5E1") }
                            Keys.onReturnPressed: securityPanel.submit()
                        }
                    }
                }

                Text {
                    Layout.fillWidth: true
                    visible: securityPanel.selected && securityPanel.selected.fields.length === 0
                    text: "Esta ação não precisa de nenhum dado — é só clicar em EXECUTAR."
                    color: textMuted; font.pixelSize: 9
                }

                Item { Layout.fillHeight: true }

                RowLayout {
                    Layout.fillWidth: true
                    Item { Layout.fillWidth: true }
                    JarvisButton {
                        variant: "secondary"
                        width: 110; height: 40; text: "✕  CANCELAR"
                        onClicked: securityPanel.back()
                    }
                    JarvisButton {
                        variant: "success"
                        width: 150; height: 40; text: "▶  EXECUTAR"
                        enabled: !jarvisBackend.busy
                        onClicked: securityPanel.submit()
                    }
                }
            }
        }
    }

    // ============================================== ASSISTENTE DE CÓDIGO
    Popup {
        id: codePanel
        objectName: "codePanel"
        parent: Overlay.overlay
        anchors.centerIn: parent

        readonly property int cols: width > 560 ? 3 : 2
        readonly property int gridRows: Math.ceil(
            jarvisBackend.codeActions.length / cols)

        width: Math.min(window.width - 100, 660)
        height: selected
                ? Math.min(window.height - 60, 210 + codeFormRepeater.count * 96)
                : Math.min(window.height - 60, 108 + gridRows * 58)
        modal: true
        focus: true
        padding: 0
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

        property var selected: null
        readonly property var longKeys: ["descricao", "tarefa", "codigo"]

        function pick(action) { selected = action }
        function back() { selected = null }
        function submit() {
            if (!selected) return
            var params = {}
            for (var i = 0; i < codeFormRepeater.count; i++) {
                var it = codeFormRepeater.itemAt(i)
                if (it) params[it.fieldKey] = it.fieldValue
            }
            jarvisBackend.runCodeAction(selected.id, params)
            selected = null
            codePanel.close()
        }

        onOpened: selected = null

        Overlay.modal: Rectangle { color: window.isDark ? "#CC020712" : "#80000000" }
        background: Rectangle { radius: 15; color: window.isDark ? "#081122" : "#FFFFFF"; border.color: window.isDark ? "#26516A" : "#CBD5E1"; border.width: 1 }

        contentItem: ColumnLayout {
            anchors.fill: parent
            anchors.margins: 18
            spacing: 10

            RowLayout {
                Layout.fillWidth: true
                JarvisButton {
                    variant: "secondary"
                    visible: codePanel.selected !== null
                    text: "‹  VOLTAR"
                    implicitHeight: 30; leftPadding: 8; rightPadding: 8; textSize: 9
                    onClicked: codePanel.back()
                }
                Text {
                    Layout.fillWidth: true
                    text: codePanel.selected
                          ? (codePanel.selected.icon + "  " + codePanel.selected.label.toUpperCase())
                          : "💻  ASSISTENTE DE CÓDIGO"
                    color: textPrimary; font.pixelSize: 14; font.weight: Font.DemiBold; font.letterSpacing: 1.2
                    elide: Text.ElideRight
                }
                JarvisButton {
                    variant: "close"
                    Layout.preferredWidth: 32
                    Layout.preferredHeight: 32
                    Layout.alignment: Qt.AlignVCenter
                    text: "✕"
                    textSize: 12
                    onClicked: codePanel.close()
                }
            }

            Text {
                Layout.fillWidth: true
                visible: codePanel.selected === null
                text: "O agente lê o repositório, explica o que encontrar e só edita arquivos com a sua confirmação. Trabalha na pasta de trabalho do perfil Desenvolvimento."
                color: textMuted; font.pixelSize: 9; wrapMode: Text.Wrap
            }

            GridLayout {
                visible: codePanel.selected === null
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.alignment: Qt.AlignTop
                columns: codePanel.cols
                columnSpacing: 8
                rowSpacing: 8

                Repeater {
                    model: jarvisBackend.codeActions
                    delegate: Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 54
                        radius: 9
                        color: caMouse.containsMouse ? (window.isDark ? "#123247" : "#E0F2FE") : (window.isDark ? "#0B1B2E" : "#F8FAFC")
                        border.color: caMouse.containsMouse ? cyan : (window.isDark ? "#1F3B57" : "#CBD5E1")
                        Column {
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.verticalCenter: parent.verticalCenter
                            anchors.leftMargin: 9
                            anchors.rightMargin: 9
                            spacing: 1
                            Text {
                                text: modelData.icon + "  " + modelData.label
                                color: textPrimary; font.pixelSize: 10; font.weight: Font.DemiBold
                                elide: Text.ElideRight; width: parent.width
                            }
                            Text {
                                text: modelData.description
                                color: textMuted; font.pixelSize: 8
                                elide: Text.ElideRight; width: parent.width
                            }
                        }
                        MouseArea {
                            id: caMouse
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: codePanel.pick(modelData)
                        }
                    }
                }
            }

            ColumnLayout {
                visible: codePanel.selected !== null
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: 10

                Text {
                    Layout.fillWidth: true
                    text: codePanel.selected ? codePanel.selected.description : ""
                    color: textMuted; font.pixelSize: 10; wrapMode: Text.Wrap
                }

                Repeater {
                    id: codeFormRepeater
                    model: codePanel.selected ? codePanel.selected.fields : []
                    delegate: ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 4
                        readonly property bool isLong: codePanel.longKeys.indexOf(modelData.key) >= 0
                        property string fieldKey: modelData.key
                        property string fieldValue: isLong ? caArea.text : caField.text
                        Text {
                            text: modelData.label + (modelData.optional ? "  (opcional)" : "")
                            color: textMuted; font.pixelSize: 8; font.letterSpacing: 1
                        }
                        TextField {
                            id: caField
                            visible: !parent.isLong
                            Layout.fillWidth: true; Layout.preferredHeight: 38
                            text: modelData.default || ""
                            placeholderText: modelData.placeholder
                            placeholderTextColor: window.isDark ? "#526D83" : "#94A3B8"; color: textPrimary; font.pixelSize: 12; leftPadding: 12
                            background: Rectangle { radius: 9; color: window.isDark ? "#0D1D33" : "#FFFFFF"; border.color: parent.activeFocus ? cyan : (window.isDark ? "#23435E" : "#CBD5E1") }
                            Keys.onReturnPressed: codePanel.submit()
                        }
                        Rectangle {
                            visible: parent.isLong
                            Layout.fillWidth: true
                            Layout.preferredHeight: 78
                            radius: 9
                            color: window.isDark ? "#0D1D33" : "#FFFFFF"
                            border.color: caArea.activeFocus ? cyan : (window.isDark ? "#23435E" : "#CBD5E1")
                            ScrollView {
                                anchors.fill: parent
                                anchors.margins: 8
                                TextArea {
                                    id: caArea
                                    placeholderText: modelData.placeholder
                                    placeholderTextColor: window.isDark ? "#526D83" : "#94A3B8"
                                    color: textPrimary; font.pixelSize: 12
                                    wrapMode: TextArea.Wrap
                                    background: null
                                }
                            }
                        }
                    }
                }

                Item { Layout.fillHeight: true }

                RowLayout {
                    Layout.fillWidth: true
                    Item { Layout.fillWidth: true }
                    JarvisButton {
                        variant: "secondary"
                        width: 110; height: 40; text: "✕  CANCELAR"
                        onClicked: codePanel.back()
                    }
                    JarvisButton {
                        variant: "success"
                        width: 150; height: 40; text: "▶  EXECUTAR"
                        enabled: !jarvisBackend.busy
                        onClicked: codePanel.submit()
                    }
                }
            }
        }
    }

    FolderDialog {
        id: devFolderDialog
        title: "Escolher a pasta de trabalho (Desenvolvimento)"
        property string pendingProfile: "desenvolvimento"
        onAccepted: jarvisBackend.setProfileFolder(
            pendingProfile, window.urlToPath(selectedFolder)
        )
    }

    // ============================================== APOIO CLÍNICO (SETOR SAÚDE)
    Popup {
        id: healthPanel
        objectName: "healthPanel"
        parent: Overlay.overlay
        anchors.centerIn: parent

        readonly property int cols: width > 560 ? 3 : 2
        readonly property int gridRows: Math.ceil(jarvisBackend.healthActions.length / cols)

        width: Math.min(window.width - 100, 680)
        height: selected
                ? Math.min(window.height - 60, 240 + healthFormRepeater.count * 110)
                : Math.min(window.height - 60, 140 + gridRows * 58)
        modal: true
        focus: true
        padding: 0
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

        property var selected: null

        function pick(action) { selected = action }
        function back() { selected = null }
        function submit() {
            if (!selected) return
            var params = {}
            for (var i = 0; i < healthFormRepeater.count; i++) {
                var it = healthFormRepeater.itemAt(i)
                if (it) params[it.fieldKey] = it.fieldValue
            }
            jarvisBackend.runHealthAction(selected.id, params)
            selected = null
            healthPanel.close()
        }

        onOpened: selected = null

        Overlay.modal: Rectangle { color: window.isDark ? "#CC020712" : "#80000000" }
        background: Rectangle { radius: 15; color: window.isDark ? "#081122" : "#FFFFFF"; border.color: window.isDark ? "#26516A" : "#CBD5E1"; border.width: 1 }

        contentItem: ColumnLayout {
            anchors.fill: parent
            anchors.margins: 18
            spacing: 10

            RowLayout {
                Layout.fillWidth: true
                JarvisButton {
                    variant: "secondary"
                    visible: healthPanel.selected !== null
                    text: "‹  VOLTAR"
                    implicitHeight: 30; leftPadding: 8; rightPadding: 8; textSize: 9
                    onClicked: healthPanel.back()
                }
                Text {
                    Layout.fillWidth: true
                    text: healthPanel.selected
                          ? (healthPanel.selected.icon + "  " + healthPanel.selected.label.toUpperCase())
                          : "🩺  APOIO CLÍNICO"
                    color: textPrimary; font.pixelSize: 14; font.weight: Font.DemiBold; font.letterSpacing: 1.2
                    elide: Text.ElideRight
                }
                JarvisButton {
                    variant: "close"
                    Layout.preferredWidth: 32
                    Layout.preferredHeight: 32
                    Layout.alignment: Qt.AlignVCenter
                    text: "✕"
                    textSize: 12
                    onClicked: healthPanel.close()
                }
            }

            Text {
                Layout.fillWidth: true
                visible: healthPanel.selected === null
                text: "Apoio ao PROFISSIONAL. Toda resposta é rascunho para você revisar e assumir — não é diagnóstico nem prescrição final, e não fala direto com o paciente. Não coloque dados que identifiquem o paciente."
                color: "#F6C453"; font.pixelSize: 9; wrapMode: Text.Wrap
            }

            GridLayout {
                visible: healthPanel.selected === null
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.alignment: Qt.AlignTop
                columns: healthPanel.cols
                columnSpacing: 8
                rowSpacing: 8

                Repeater {
                    model: jarvisBackend.healthActions
                    delegate: Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 54
                        radius: 9
                        color: haMouse.containsMouse ? (window.isDark ? "#123247" : "#E0F2FE") : (window.isDark ? "#0B1B2E" : "#F8FAFC")
                        border.color: haMouse.containsMouse ? cyan : (window.isDark ? "#1F3B57" : "#CBD5E1")
                        Column {
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.verticalCenter: parent.verticalCenter
                            anchors.leftMargin: 9
                            anchors.rightMargin: 9
                            spacing: 1
                            Text {
                                text: modelData.icon + "  " + modelData.label
                                color: textPrimary; font.pixelSize: 10; font.weight: Font.DemiBold
                                elide: Text.ElideRight; width: parent.width
                            }
                            Text {
                                text: modelData.description
                                color: textMuted; font.pixelSize: 8
                                elide: Text.ElideRight; width: parent.width
                            }
                        }
                        MouseArea {
                            id: haMouse
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: healthPanel.pick(modelData)
                        }
                    }
                }
            }

            ColumnLayout {
                visible: healthPanel.selected !== null
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: 10

                Text {
                    Layout.fillWidth: true
                    text: healthPanel.selected ? healthPanel.selected.description : ""
                    color: textMuted; font.pixelSize: 10; wrapMode: Text.Wrap
                }

                Repeater {
                    id: healthFormRepeater
                    model: healthPanel.selected ? healthPanel.selected.fields : []
                    delegate: ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 4
                        readonly property bool isLong: modelData.long === true
                        property string fieldKey: modelData.key
                        property string fieldValue: isLong ? haArea.text : haField.text
                        Text {
                            text: modelData.label + (modelData.optional ? "  (opcional)" : "")
                            color: textMuted; font.pixelSize: 8; font.letterSpacing: 1
                        }
                        TextField {
                            id: haField
                            visible: !parent.isLong
                            Layout.fillWidth: true; Layout.preferredHeight: 38
                            text: modelData.default || ""
                            placeholderText: modelData.placeholder
                            placeholderTextColor: window.isDark ? "#526D83" : "#94A3B8"; color: textPrimary; font.pixelSize: 12; leftPadding: 12
                            background: Rectangle { radius: 9; color: window.isDark ? "#0D1D33" : "#FFFFFF"; border.color: parent.activeFocus ? cyan : (window.isDark ? "#23435E" : "#CBD5E1") }
                            Keys.onReturnPressed: healthPanel.submit()
                        }
                        Rectangle {
                            visible: parent.isLong
                            Layout.fillWidth: true
                            Layout.preferredHeight: 92
                            radius: 9
                            color: window.isDark ? "#0D1D33" : "#FFFFFF"
                            border.color: haArea.activeFocus ? cyan : (window.isDark ? "#23435E" : "#CBD5E1")
                            ScrollView {
                                anchors.fill: parent
                                anchors.margins: 8
                                clip: true
                                TextArea {
                                    id: haArea
                                    placeholderText: modelData.placeholder
                                    placeholderTextColor: window.isDark ? "#526D83" : "#94A3B8"
                                    color: textPrimary; font.pixelSize: 12
                                    wrapMode: TextArea.Wrap
                                    background: null
                                }
                            }
                        }
                    }
                }

                Item { Layout.fillHeight: true }

                RowLayout {
                    Layout.fillWidth: true
                    Item { Layout.fillWidth: true }
                    JarvisButton {
                        variant: "secondary"
                        width: 110; height: 40; text: "✕  CANCELAR"
                        onClicked: healthPanel.back()
                    }
                    JarvisButton {
                        variant: "success"
                        width: 150; height: 40; text: "▶  GERAR"
                        enabled: !jarvisBackend.busy
                        onClicked: healthPanel.submit()
                    }
                }
            }
        }
    }

    // ============================================== MODAL: CADASTRO DE PACIENTE
    Popup {
        id: patientModal
        objectName: "patientModal"
        parent: Overlay.overlay
        anchors.centerIn: parent
        width: Math.min(window.width - 120, 760)
        height: Math.min(window.height - 80, 720)
        modal: true; focus: true; padding: 0
        closePolicy: Popup.CloseOnEscape

        property int pid: -1
        readonly property var sexIds: ["", "M", "F", "O"]

        function openNew() { pid = -1; load({}); open() }
        function openEdit(id) { pid = id; load(jarvisBackend.patientDetail(id)); open() }
        function load(p) {
            fName.text = p.name || ""
            fBirth.text = p.birthdate || ""
            fSex.currentIndex = Math.max(0, sexIds.indexOf(p.sex || ""))
            fPhone.text = p.phone || ""; fEmail.text = p.email || ""
            fDoc.text = p.document || ""; fCns.text = p.cns || ""
            fBlood.text = p.blood_type || ""
            fAllergies.text = p.allergies || ""; fConditions.text = p.conditions || ""
            fMeds.text = p.medications || ""
            fBg.text = p.background || ""; fFam.text = p.family_background || ""
            fSoc.text = p.social_background || ""
            fInsurance.text = p.insurance || ""; fEmerg.text = p.emergency_contact || ""
            fCity.text = p.city || ""; fNotes.text = p.notes || ""
        }
        function save() {
            var d = {
                "id": pid > 0 ? pid : 0,
                "name": fName.text, "birthdate": fBirth.text, "sex": sexIds[fSex.currentIndex],
                "phone": fPhone.text, "email": fEmail.text, "document": fDoc.text, "cns": fCns.text,
                "blood_type": fBlood.text, "allergies": fAllergies.text, "conditions": fConditions.text,
                "medications": fMeds.text, "background": fBg.text, "family_background": fFam.text,
                "social_background": fSoc.text, "insurance": fInsurance.text,
                "emergency_contact": fEmerg.text, "city": fCity.text, "notes": fNotes.text
            }
            var id = jarvisBackend.savePatient(d)
            if (id > 0) { pid = id; close() }
        }

        Overlay.modal: Rectangle { color: window.isDark ? "#CC020712" : "#80000000" }
        background: Rectangle { radius: 16; color: window.isDark ? "#0B1526" : "#FFFFFF"; border.color: window.isDark ? "#26516A" : "#CBD5E1"; border.width: 1 }

        component PField : TextField {
            Layout.fillWidth: true; Layout.preferredHeight: 36
            color: textPrimary; font.pixelSize: 11; leftPadding: 10
            placeholderTextColor: window.isDark ? "#526D83" : "#94A3B8"
            background: Rectangle { radius: 8; color: inputBg; border.color: parent.activeFocus ? cyan : inputBorder }
        }
        component PLbl : Text { color: textMuted; font.pixelSize: 8; font.letterSpacing: 1 }

        contentItem: ColumnLayout {
            anchors.fill: parent
            anchors.margins: 20
            spacing: 12

            RowLayout {
                Layout.fillWidth: true
                Text { Layout.fillWidth: true; text: patientModal.pid > 0 ? "FICHA DO PACIENTE" : "NOVO PACIENTE"; color: textPrimary; font.pixelSize: 15; font.weight: Font.DemiBold; font.letterSpacing: 1.5 }
                JarvisButton { variant: "close"; text: "✕"; implicitWidth: 32; implicitHeight: 32; onClicked: patientModal.close() }
            }

            ScrollView {
                Layout.fillWidth: true; Layout.fillHeight: true
                contentWidth: availableWidth
                clip: true
                GridLayout {
                    width: parent.width
                    columns: 3
                    columnSpacing: 12
                    rowSpacing: 8

                    ColumnLayout { Layout.columnSpan: 2; spacing: 3; PLbl { text: "NOME COMPLETO *" } PField { id: fName; placeholderText: "nome do paciente" } }
                    ColumnLayout { spacing: 3; PLbl { text: "NASCIMENTO (AAAA-MM-DD)" } PField { id: fBirth; placeholderText: "1985-04-12" } }
                    ColumnLayout { spacing: 3; PLbl { text: "SEXO" } FuturisticCombo { id: fSex; Layout.fillWidth: true; Layout.preferredHeight: 36; model: ["—", "Masculino", "Feminino", "Outro"] } }
                    ColumnLayout { spacing: 3; PLbl { text: "TELEFONE" } PField { id: fPhone; placeholderText: "(11) 90000-0000" } }
                    ColumnLayout { spacing: 3; PLbl { text: "TIPO SANGUÍNEO" } PField { id: fBlood; placeholderText: "O+" } }
                    ColumnLayout { spacing: 3; PLbl { text: "E-MAIL" } PField { id: fEmail; placeholderText: "email@exemplo.com" } }
                    ColumnLayout { spacing: 3; PLbl { text: "DOCUMENTO / PRONTUÁRIO" } PField { id: fDoc; placeholderText: "CPF ou nº" } }
                    ColumnLayout { spacing: 3; PLbl { text: "CNS (Cartão SUS)" } PField { id: fCns; placeholderText: "000 0000 0000 0000" } }
                    ColumnLayout { spacing: 3; PLbl { text: "CIDADE / UF" } PField { id: fCity; placeholderText: "São Paulo / SP" } }

                    ColumnLayout { Layout.columnSpan: 3; spacing: 3; PLbl { text: "ALERGIAS" } PField { id: fAllergies; placeholderText: "dipirona, penicilina, látex..." } }
                    ColumnLayout { Layout.columnSpan: 3; spacing: 3; PLbl { text: "CONDIÇÕES CRÔNICAS / COMORBIDADES" } PField { id: fConditions; placeholderText: "HAS, DM2, asma..." } }
                    ColumnLayout { Layout.columnSpan: 3; spacing: 3; PLbl { text: "MEDICAÇÕES EM USO (separe por vírgula)" } PField { id: fMeds; placeholderText: "losartana 50mg, metformina 850mg, AAS 100mg" } }
                    ColumnLayout { Layout.columnSpan: 3; spacing: 3; PLbl { text: "ANTECEDENTES PESSOAIS" } PField { id: fBg; placeholderText: "cirurgias, internações, tabagismo..." } }
                    ColumnLayout { Layout.columnSpan: 3; spacing: 3; PLbl { text: "HISTÓRICO FAMILIAR" } PField { id: fFam; placeholderText: "IAM precoce no pai, DM2 na mãe..." } }
                    ColumnLayout { Layout.columnSpan: 3; spacing: 3; PLbl { text: "HISTÓRICO SOCIAL" } PField { id: fSoc; placeholderText: "profissão, moradia, atividade física, álcool..." } }
                    ColumnLayout { Layout.columnSpan: 2; spacing: 3; PLbl { text: "CONVÊNIO / PLANO" } PField { id: fInsurance; placeholderText: "convênio e carteirinha" } }
                    ColumnLayout { spacing: 3; PLbl { text: "CONTATO DE EMERGÊNCIA" } PField { id: fEmerg; placeholderText: "nome e telefone" } }
                    ColumnLayout { Layout.columnSpan: 3; spacing: 3; PLbl { text: "OBSERVAÇÕES" } PField { id: fNotes; placeholderText: "" } }
                }
            }

            RowLayout {
                Layout.fillWidth: true
                JarvisButton {
                    variant: "danger"; text: "✕  EXCLUIR"; implicitHeight: 38
                    visible: patientModal.pid > 0
                    onClicked: { jarvisBackend.deletePatient(patientModal.pid); patientModal.close() }
                }
                JarvisButton {
                    variant: "secondary"; text: "🗂  PRONTUÁRIO"; implicitHeight: 38; textSize: 9
                    visible: patientModal.pid > 0
                    onClicked: { window.activePatientId = patientModal.pid; patientModal.close(); jarvisBackend.setView("laudos") }
                }
                Item { Layout.fillWidth: true }
                JarvisButton { variant: "success"; text: "✔  SALVAR"; implicitHeight: 38; textSize: 10; onClicked: patientModal.save() }
            }
        }
    }

    // ============================================== MODAL: REGISTRO / LAUDO
    Popup {
        id: recordModal
        objectName: "recordModal"
        parent: Overlay.overlay
        anchors.centerIn: parent
        width: Math.min(window.width - 120, 820)
        height: Math.min(window.height - 70, 780)
        modal: true; focus: true; padding: 0
        closePolicy: Popup.CloseOnEscape

        property int rid: -1
        property int pid: -1
        property var rec: ({})
        property var vitalsObj: ({})
        readonly property var kindIds: ["laudo", "exame", "consulta", "evolucao", "prescricao", "nota"]

        function openNew(patientId) {
            rid = -1; pid = patientId; rec = ({}); vitalsObj = ({})
            rKind.currentIndex = 0; rTitle.text = ""; rDate.text = ""; rBody.text = ""
            open()
        }
        function openEdit(recordId, patientId) {
            rid = recordId; pid = patientId
            rec = jarvisBackend.recordDetail(recordId) || ({})
            rKind.currentIndex = Math.max(0, kindIds.indexOf(rec.kind || "nota"))
            rTitle.text = rec.title || ""; rDate.text = rec.occurred_at || ""; rBody.text = rec.body || ""
            try { vitalsObj = JSON.parse(rec.vitals || "{}") } catch(e) { vitalsObj = ({}) }
            open()
        }
        function save(thenClose) {
            var d = {
                "id": rid > 0 ? rid : 0, "patient_id": pid,
                "kind": kindIds[rKind.currentIndex], "title": rTitle.text,
                "occurred_at": rDate.text, "body": rBody.text,
                "vitals": JSON.stringify(vitalsObj)
            }
            var id = jarvisBackend.saveRecord(d)
            if (id > 0) { rid = id; rec = jarvisBackend.recordDetail(id) || rec; if (thenClose) close() }
            return id
        }
        function analyze() {
            var id = rid > 0 ? rid : save(false)
            if (id > 0) { jarvisBackend.analyzeRecord(id); close() }
        }

        Connections {
            target: jarvisBackend
            function onPatientRecordsChanged() {
                if (recordModal.visible && recordModal.rid > 0)
                    recordModal.rec = jarvisBackend.recordDetail(recordModal.rid) || recordModal.rec
            }
        }

        Overlay.modal: Rectangle { color: window.isDark ? "#CC020712" : "#80000000" }
        background: Rectangle { radius: 16; color: window.isDark ? "#0B1526" : "#FFFFFF"; border.color: window.isDark ? "#26516A" : "#CBD5E1"; border.width: 1 }

        component RLbl : Text { color: textMuted; font.pixelSize: 8; font.letterSpacing: 1 }
        component RField : TextField {
            Layout.fillWidth: true; Layout.preferredHeight: 36
            color: textPrimary; font.pixelSize: 11; leftPadding: 10
            placeholderTextColor: window.isDark ? "#526D83" : "#94A3B8"
            background: Rectangle { radius: 8; color: inputBg; border.color: parent.activeFocus ? cyan : inputBorder }
        }

        contentItem: ColumnLayout {
            anchors.fill: parent
            anchors.margins: 20
            spacing: 10

            RowLayout {
                Layout.fillWidth: true
                Text {
                    Layout.fillWidth: true
                    text: (recordModal.rid > 0 ? "REGISTRO" : "NOVO REGISTRO")
                    color: textPrimary; font.pixelSize: 15; font.weight: Font.DemiBold; font.letterSpacing: 1.5
                }
                JarvisButton { variant: "close"; text: "✕"; implicitWidth: 32; implicitHeight: 32; onClicked: recordModal.close() }
            }

            ScrollView {
                Layout.fillWidth: true; Layout.fillHeight: true
                contentWidth: availableWidth
                clip: true
                ColumnLayout {
                    width: parent.width
                    spacing: 10

                    RowLayout {
                        Layout.fillWidth: true; spacing: 10
                        ColumnLayout { Layout.preferredWidth: 170; spacing: 3
                            RLbl { text: "TIPO" }
                            FuturisticCombo { id: rKind; Layout.fillWidth: true; Layout.preferredHeight: 36; model: jarvisBackend.recordKinds.map(function(k){ return k.label }) }
                        }
                        ColumnLayout { Layout.fillWidth: true; spacing: 3
                            RLbl { text: "TÍTULO" }
                            RField { id: rTitle; placeholderText: "ex.: Hemograma completo, RM de crânio" }
                        }
                        ColumnLayout { Layout.preferredWidth: 150; spacing: 3
                            RLbl { text: "DATA (AAAA-MM-DD)" }
                            RField { id: rDate; placeholderText: "2026-08-20" }
                        }
                    }

                    RLbl { text: "TEXTO DO LAUDO / RESULTADO / EVOLUÇÃO" }
                    Rectangle {
                        Layout.fillWidth: true; Layout.preferredHeight: 130
                        radius: 8; color: inputBg; border.color: rBody.activeFocus ? cyan : inputBorder
                        ScrollView { anchors.fill: parent; anchors.margins: 8; clip: true
                            TextArea {
                                id: rBody
                                placeholderText: "cole aqui o texto do laudo/resultado, ou anexe o arquivo abaixo"
                                placeholderTextColor: window.isDark ? "#526D83" : "#94A3B8"
                                color: textPrimary; font.pixelSize: 11; wrapMode: TextArea.Wrap; background: null
                            }
                        }
                    }

                    RLbl { text: "SINAIS VITAIS (opcional)" }
                    GridLayout {
                        Layout.fillWidth: true
                        columns: 3
                        columnSpacing: 10; rowSpacing: 6
                        Repeater {
                            model: jarvisBackend.vitalFields
                            delegate: ColumnLayout {
                                Layout.fillWidth: true; spacing: 2
                                Text { text: modelData.label + (modelData.unit ? " (" + modelData.unit + ")" : ""); color: textMuted; font.pixelSize: 8 }
                                TextField {
                                    Layout.fillWidth: true; Layout.preferredHeight: 32
                                    color: textPrimary; font.pixelSize: 11; leftPadding: 8
                                    background: Rectangle { radius: 7; color: inputBg; border.color: parent.activeFocus ? cyan : inputBorder }
                                    Component.onCompleted: text = recordModal.vitalsObj[modelData.key] || ""
                                    onTextChanged: { var o = recordModal.vitalsObj; o[modelData.key] = text; recordModal.vitalsObj = o }
                                }
                            }
                        }
                    }

                    // ---- anexos
                    RowLayout {
                        Layout.fillWidth: true
                        RLbl { text: "ANEXOS  (PDF, imagem, Word, Excel)"; Layout.fillWidth: true }
                        JarvisButton {
                            variant: "secondary"; text: "📎 ANEXAR"; implicitHeight: 28; textSize: 8
                            onClicked: {
                                if (recordModal.rid <= 0) recordModal.save(false)
                                if (recordModal.rid > 0) recordFileDialog.open()
                            }
                        }
                    }
                    Repeater {
                        model: recordModal.rid > 0 ? jarvisBackend.recordFiles(recordModal.rid) : []
                        delegate: Rectangle {
                            Layout.fillWidth: true; Layout.preferredHeight: 34
                            radius: 8; color: window.isDark ? "#0C1E33" : "#F8FAFC"
                            border.color: window.isDark ? "#23435E" : "#E2E8F0"
                            RowLayout {
                                anchors.fill: parent; anchors.leftMargin: 10; anchors.rightMargin: 6
                                spacing: 8
                                Text { text: modelData.mime === "image" ? "🖼" : "📄"; font.pixelSize: 12 }
                                Text { Layout.fillWidth: true; text: modelData.name; color: textPrimary; font.pixelSize: 9; elide: Text.ElideMiddle }
                                Text { text: modelData.sizeLabel + (modelData.hasText ? "  · texto lido" : ""); color: textMuted; font.pixelSize: 8 }
                                JarvisButton { variant: "danger"; text: "✕"; implicitWidth: 24; implicitHeight: 24; onClicked: jarvisBackend.deleteRecordFile(modelData.id) }
                            }
                        }
                    }

                    // ---- análise da IA
                    JarvisButton {
                        Layout.fillWidth: true
                        variant: "success"; implicitHeight: 42
                        enabled: !jarvisBackend.busy
                        text: "🩺  LER LAUDO E ANALISAR  —  SEGUNDO OLHAR SOBRE O CASO"
                        textSize: 9
                        onClicked: recordModal.analyze()
                    }
                    Rectangle {
                        Layout.fillWidth: true
                        visible: (recordModal.rec.aiFull || "") !== ""
                        Layout.preferredHeight: aiCol.implicitHeight + 24
                        radius: 10
                        color: {
                            var r = recordModal.rec.risk || ""
                            if (r === "critico" || r === "alto") return window.isDark ? "#1E0B12" : "#FEF2F2"
                            if (r === "moderado") return window.isDark ? "#1B1408" : "#FFFBEB"
                            return window.isDark ? "#08131F" : "#F0FDF4"
                        }
                        border.color: {
                            var r = recordModal.rec.risk || ""
                            if (r === "critico" || r === "alto") return danger
                            if (r === "moderado") return amber
                            return window.isDark ? "#1E5C43" : "#BBF7D0"
                        }
                        Column {
                            id: aiCol
                            x: 12; y: 12
                            width: parent.width - 24
                            spacing: 6
                            Text { text: "SEGUNDO OLHAR DA IA  —  rascunho, revise antes de qualquer conduta"; color: textMuted; font.pixelSize: 8; font.weight: Font.Bold; font.letterSpacing: 1 }
                            Text { width: parent.width; text: recordModal.rec.aiFull || ""; color: textPrimary; font.pixelSize: 10; wrapMode: Text.Wrap; textFormat: Text.MarkdownText }
                        }
                    }
                }
            }

            RowLayout {
                Layout.fillWidth: true
                JarvisButton {
                    variant: "danger"; text: "✕  EXCLUIR"; implicitHeight: 38
                    visible: recordModal.rid > 0
                    onClicked: { jarvisBackend.deleteRecord(recordModal.rid); recordModal.close() }
                }
                Item { Layout.fillWidth: true }
                JarvisButton { variant: "success"; text: "✔  SALVAR"; implicitHeight: 38; textSize: 10; onClicked: recordModal.save(true) }
            }
        }

        FileDialog {
            id: recordFileDialog
            title: "Anexar ao registro"
            nameFilters: ["Documentos e imagens (*.pdf *.png *.jpg *.jpeg *.webp *.docx *.txt *.xlsx)", "Todos (*)"]
            onAccepted: jarvisBackend.attachToRecord(recordModal.rid, recordModal.pid, selectedFile)
        }
    }

    // ============================================== HISTÓRICO DE CONVERSAS
    Popup {
        id: historyDialog
        objectName: "historyDialog"
        parent: Overlay.overlay
        anchors.centerIn: parent
        width: Math.min(window.width - 160, 520)
        height: Math.min(window.height - 140, 560)
        modal: true
        focus: true
        padding: 0
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

        Overlay.modal: Rectangle { color: window.isDark ? "#CC020712" : "#80000000" }
        background: Rectangle { radius: 15; color: window.isDark ? "#081122" : "#FFFFFF"; border.color: window.isDark ? "#26516A" : "#CBD5E1"; border.width: 1 }

        contentItem: ColumnLayout {
            anchors.fill: parent
            anchors.margins: 20
            spacing: 12

            RowLayout {
                Layout.fillWidth: true
                Text {
                    Layout.fillWidth: true
                    text: "HISTÓRICO DE CONVERSAS"
                    color: textPrimary; font.pixelSize: 15; font.weight: Font.DemiBold; font.letterSpacing: 1.4
                }
                JarvisButton {
                    text: "+  NOVA"
                    enabled: !jarvisBackend.busy
                    onClicked: { jarvisBackend.newConversation(); historyDialog.close() }
                }
            }

            Text {
                Layout.fillWidth: true
                text: "Clique numa conversa para reabrir."
                color: textMuted; font.pixelSize: 9; wrapMode: Text.Wrap
            }

            ListView {
                id: historyList
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                spacing: 6
                model: jarvisBackend.conversations
                ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }

                delegate: Rectangle {
                    width: historyList.width
                    height: 54
                    radius: 9
                    color: modelData.current ? (window.isDark ? "#123247" : "#E0F2FE")
                           : (rowMouse.containsMouse ? (window.isDark ? "#0F2338" : "#F1F5F9") : (window.isDark ? "#0B1B2E" : "#F8FAFC"))
                    border.color: modelData.current ? cyan : (window.isDark ? "#1F3B57" : "#CBD5E1")

                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: 12
                        anchors.rightMargin: 8
                        spacing: 8
                        Column {
                            Layout.fillWidth: true
                            spacing: 2
                            Text {
                                text: modelData.title
                                color: textPrimary; font.pixelSize: 11; font.weight: Font.Medium
                                elide: Text.ElideRight
                                width: historyList.width - 90
                            }
                            Text {
                                text: modelData.when + "  ·  " + modelData.turns + " msg"
                                color: textMuted; font.pixelSize: 8
                            }
                        }
                        JarvisButton {
                            variant: "danger"
                            Layout.preferredWidth: 32
                            Layout.preferredHeight: 32
                            Layout.alignment: Qt.AlignVCenter
                            text: "✕"
                            textSize: 11
                            ToolTip.visible: hovered
                            ToolTip.text: "Excluir conversa"
                            ToolTip.delay: 300
                            onClicked: jarvisBackend.deleteConversation(modelData.id)
                        }
                    }
                    MouseArea {
                        id: rowMouse
                        anchors.fill: parent
                        anchors.rightMargin: 38
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: { jarvisBackend.openConversation(modelData.id); historyDialog.close() }
                    }
                }

                Text {
                    anchors.centerIn: parent
                    visible: jarvisBackend.conversations.length === 0
                    text: "Nenhuma conversa salva ainda."
                    color: textMuted; font.pixelSize: 10
                }
            }

            JarvisButton {
                variant: "secondary"
                Layout.alignment: Qt.AlignRight
                width: 110; height: 38; text: "✕  FECHAR"
                onClicked: historyDialog.close()
            }
        }
    }

    // ============================================== SERVIDORES (SSH)
    Popup {
        id: serverManager
        objectName: "serverManager"
        parent: Overlay.overlay
        anchors.centerIn: parent
        width: Math.min(window.width - 140, 560)
        height: Math.min(window.height - 120, 520)
        modal: true
        focus: true
        padding: 0
        closePolicy: Popup.CloseOnEscape

        property string testAlias: ""
        property string testResult: ""
        property bool testing: false

        Overlay.modal: Rectangle { color: window.isDark ? "#CC020712" : "#80000000" }
        background: Rectangle { radius: 15; color: window.isDark ? "#081122" : "#FFFFFF"; border.color: window.isDark ? "#26516A" : "#CBD5E1"; border.width: 1 }

        contentItem: ColumnLayout {
            anchors.fill: parent
            anchors.margins: 20
            spacing: 12

            RowLayout {
                Layout.fillWidth: true
                Text {
                    Layout.fillWidth: true
                    text: "SERVIDORES SSH"
                    color: textPrimary; font.pixelSize: 15; font.weight: Font.DemiBold; font.letterSpacing: 1.6
                }
                JarvisButton {
                    text: "+  ADICIONAR"
                    onClicked: serverEditor.openFor(null)
                }
            }

            Text {
                Layout.fillWidth: true
                text: "Os dados de acesso ficam cifrados. Todo comando remoto pede confirmação no chat."
                color: textMuted; font.pixelSize: 9; wrapMode: Text.Wrap
            }

            ScrollView {
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                ColumnLayout {
                    width: serverManager.width - 40
                    spacing: 8

                    Repeater {
                        model: jarvisBackend.servers
                        delegate: Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 62
                            radius: 10
                            color: window.isDark ? "#0C1E33" : "#F8FAFC"
                            border.color: window.isDark ? "#23435E" : "#CBD5E1"
                            RowLayout {
                                anchors.fill: parent
                                anchors.margins: 10
                                spacing: 8
                                Column {
                                    Layout.fillWidth: true
                                    spacing: 2
                                    Text { text: modelData.alias; color: textPrimary; font.pixelSize: 12; font.weight: Font.DemiBold }
                                    Text {
                                        text: modelData.user + "@" + modelData.host + ":" + modelData.port
                                              + "  ·  " + modelData.auth
                                              + (modelData.auth === "password" && !modelData.hasPassword ? "  (sem senha!)" : "")
                                        color: textMuted; font.pixelSize: 9
                                    }
                                }
                                JarvisButton {
                                    variant: "secondary"
                                    text: "⚡  TESTAR"
                                    Layout.preferredHeight: 32
                                    Layout.alignment: Qt.AlignVCenter
                                    leftPadding: 10; rightPadding: 10; textSize: 8
                                    onClicked: {
                                        serverManager.testAlias = modelData.alias
                                        serverManager.testResult = ""
                                        serverManager.testing = true
                                        jarvisBackend.testServer(modelData.id)
                                    }
                                }
                                JarvisButton {
                                    text: "✎  EDITAR"
                                    Layout.preferredHeight: 32
                                    Layout.alignment: Qt.AlignVCenter
                                    leftPadding: 10; rightPadding: 10; textSize: 8
                                    onClicked: serverEditor.openFor(modelData)
                                }
                                JarvisButton {
                                    variant: "danger"
                                    Layout.preferredWidth: 32
                                    Layout.preferredHeight: 32
                                    Layout.alignment: Qt.AlignVCenter
                                    text: "✕"
                                    textSize: 11
                                    ToolTip.visible: hovered
                                    ToolTip.text: "Excluir servidor"
                                    ToolTip.delay: 300
                                    onClicked: jarvisBackend.deleteServer(modelData.id)
                                }
                            }
                        }
                    }

                    Text {
                        visible: jarvisBackend.servers.length === 0
                        Layout.fillWidth: true
                        text: "Nenhum servidor. Clique em + ADICIONAR."
                        color: textMuted; font.pixelSize: 10
                        horizontalAlignment: Text.AlignHCenter
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                visible: serverManager.testing || serverManager.testResult !== ""
                Layout.preferredHeight: Math.max(44, testOut.implicitHeight + 18)
                radius: 9
                color: window.isDark ? "#050C18" : "#F1F5F9"
                border.color: window.isDark ? "#1E3B5C" : "#CBD5E1"
                Text {
                    id: testOut
                    anchors.fill: parent
                    anchors.margins: 9
                    text: serverManager.testing
                          ? "Testando " + serverManager.testAlias + "…"
                          : (serverManager.testAlias + ": " + serverManager.testResult)
                    color: window.isDark ? "#CDE4F2" : "#0F172A"
                    font.family: "Consolas, monospace"
                    font.pixelSize: 9
                    wrapMode: Text.Wrap
                }
            }

            JarvisButton {
                variant: "secondary"
                Layout.alignment: Qt.AlignRight
                width: 110; height: 38; text: "✕  FECHAR"
                onClicked: serverManager.close()
            }
        }
    }

    Popup {
        id: serverEditor
        objectName: "serverEditor"
        parent: Overlay.overlay
        anchors.centerIn: parent
        width: Math.min(window.width - 160, 500)
        height: 500
        modal: true
        focus: true
        padding: 0
        closePolicy: Popup.CloseOnEscape

        property int editId: 0

        function openFor(s) {
            if (s) {
                editId = s.id
                seAlias.text = s.alias; seHost.text = s.host; seUser.text = s.user
                sePort.text = "" + s.port
                seAuth.currentIndex = Math.max(0, seAuth.find(s.auth))
                seKey.text = s.keyPath
                sePass.text = ""
                sePass.placeholderText = s.hasPassword ? "•••••• (guardada — deixe em branco p/ manter)" : "senha da VPS"
            } else {
                editId = 0
                seAlias.text = ""; seHost.text = ""; seUser.text = ""; sePort.text = "22"
                seAuth.currentIndex = 0; seKey.text = ""; sePass.text = ""
                sePass.placeholderText = "senha da VPS"
            }
            open()
        }

        Overlay.modal: Rectangle { color: window.isDark ? "#CC020712" : "#80000000" }
        background: Rectangle { radius: 15; color: window.isDark ? "#081122" : "#FFFFFF"; border.color: window.isDark ? "#26516A" : "#CBD5E1"; border.width: 1 }

        contentItem: ColumnLayout {
            anchors.fill: parent
            anchors.margins: 22
            spacing: 9

            Text {
                text: serverEditor.editId > 0 ? "EDITAR SERVIDOR" : "NOVO SERVIDOR"
                color: textPrimary; font.pixelSize: 15; font.weight: Font.DemiBold; font.letterSpacing: 1.6
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 10
                ColumnLayout {
                    spacing: 4
                    Text { text: "APELIDO"; color: textMuted; font.pixelSize: 8; font.letterSpacing: 1.1 }
                    TextField {
                        id: seAlias
                        Layout.preferredWidth: 150; Layout.preferredHeight: 38
                        placeholderText: "minha-vps"
                        placeholderTextColor: window.isDark ? "#526D83" : "#94A3B8"; color: textPrimary; font.pixelSize: 12; leftPadding: 12
                        background: Rectangle { radius: 9; color: window.isDark ? "#0D1D33" : "#FFFFFF"; border.color: parent.activeFocus ? cyan : (window.isDark ? "#23435E" : "#CBD5E1") }
                    }
                }
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 4
                    Text { text: "HOST / IP"; color: textMuted; font.pixelSize: 8; font.letterSpacing: 1.1 }
                    TextField {
                        id: seHost
                        Layout.fillWidth: true; Layout.preferredHeight: 38
                        placeholderText: "203.0.113.10 ou vps.meusite.com"
                        placeholderTextColor: window.isDark ? "#526D83" : "#94A3B8"; color: textPrimary; font.pixelSize: 12; leftPadding: 12
                        background: Rectangle { radius: 9; color: window.isDark ? "#0D1D33" : "#FFFFFF"; border.color: parent.activeFocus ? cyan : (window.isDark ? "#23435E" : "#CBD5E1") }
                    }
                }
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 10
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 4
                    Text { text: "USUÁRIO"; color: textMuted; font.pixelSize: 8; font.letterSpacing: 1.1 }
                    TextField {
                        id: seUser
                        Layout.fillWidth: true; Layout.preferredHeight: 38
                        placeholderText: "root ou ubuntu"
                        placeholderTextColor: window.isDark ? "#526D83" : "#94A3B8"; color: textPrimary; font.pixelSize: 12; leftPadding: 12
                        background: Rectangle { radius: 9; color: window.isDark ? "#0D1D33" : "#FFFFFF"; border.color: parent.activeFocus ? cyan : (window.isDark ? "#23435E" : "#CBD5E1") }
                    }
                }
                ColumnLayout {
                    spacing: 4
                    Text { text: "PORTA"; color: textMuted; font.pixelSize: 8; font.letterSpacing: 1.1 }
                    TextField {
                        id: sePort
                        Layout.preferredWidth: 80; Layout.preferredHeight: 38
                        text: "22"; inputMask: "9999;_"
                        color: textPrimary; font.pixelSize: 12; leftPadding: 12
                        background: Rectangle { radius: 9; color: window.isDark ? "#0D1D33" : "#FFFFFF"; border.color: parent.activeFocus ? cyan : (window.isDark ? "#23435E" : "#CBD5E1") }
                    }
                }
            }

            Text { text: "AUTENTICAÇÃO"; color: textMuted; font.pixelSize: 8; font.letterSpacing: 1.1 }
            FuturisticCombo {
                id: seAuth
                Layout.fillWidth: true
                Layout.preferredHeight: 40
                model: ["key", "password", "agent"]
            }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 4
                visible: seAuth.currentText === "key"
                Text { text: "CHAVE PRIVADA (.pem / id_ed25519)"; color: textMuted; font.pixelSize: 8; font.letterSpacing: 1.1 }
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8
                    TextField {
                        id: seKey
                        Layout.fillWidth: true; Layout.preferredHeight: 38
                        placeholderText: "vazio = usa ~/.ssh/ padrão"
                        placeholderTextColor: window.isDark ? "#526D83" : "#94A3B8"; color: textPrimary; font.pixelSize: 11; leftPadding: 12
                        background: Rectangle { radius: 9; color: window.isDark ? "#0D1D33" : "#FFFFFF"; border.color: parent.activeFocus ? cyan : (window.isDark ? "#23435E" : "#CBD5E1") }
                    }
                    JarvisButton {
                        variant: "secondary"
                        width: 38; height: 38
                        text: "📁"
                        leftPadding: 0; rightPadding: 0; textSize: 13
                        onClicked: keyFileDialog.open()
                    }
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 4
                visible: seAuth.currentText === "password"
                Text { text: "SENHA DA VPS (cifrada)"; color: textMuted; font.pixelSize: 8; font.letterSpacing: 1.1 }
                TextField {
                    id: sePass
                    Layout.fillWidth: true; Layout.preferredHeight: 38
                    echoMode: TextInput.Password
                    placeholderText: "senha da VPS"
                    placeholderTextColor: window.isDark ? "#526D83" : "#94A3B8"; color: textPrimary; font.pixelSize: 12; leftPadding: 12
                    background: Rectangle { radius: 9; color: window.isDark ? "#0D1D33" : "#FFFFFF"; border.color: parent.activeFocus ? cyan : (window.isDark ? "#23435E" : "#CBD5E1") }
                }
            }

            Text {
                Layout.fillWidth: true
                visible: seAuth.currentText === "agent"
                text: "Usa as chaves carregadas no ssh-agent do Windows."
                color: textMuted; font.pixelSize: 9; wrapMode: Text.Wrap
            }

            Item { Layout.fillHeight: true }

            RowLayout {
                Layout.fillWidth: true
                Item { Layout.fillWidth: true }
                JarvisButton {
                    variant: "secondary"
                    width: 110; height: 40; text: "✕  CANCELAR"
                    onClicked: serverEditor.close()
                }
                JarvisButton {
                    variant: "save"
                    width: 150; height: 40; text: "✔  SALVAR"
                    enabled: seAlias.text.trim() && seHost.text.trim() && seUser.text.trim()
                    onClicked: {
                        jarvisBackend.saveServer(
                            serverEditor.editId, seAlias.text, seHost.text, seUser.text,
                            parseInt(sePort.text || "22"), seAuth.currentText,
                            seKey.text, sePass.text
                        )
                        serverEditor.close()
                    }
                }
            }
        }
    }

    // ============================================== FERRAMENTA (menu Análises)
    Popup {
        id: utilityDialog
        objectName: "utilityDialog"
        parent: Overlay.overlay
        anchors.centerIn: parent
        readonly property bool hasFilesField: {
            if (!util || !util.fields) return false
            for (var i = 0; i < util.fields.length; i++)
                if (util.fields[i].kind === "files") return true
            return false
        }

        width: Math.min(window.width - 120, 680)
        height: Math.min(window.height - 80, hasFilesField ? (jarvisBackend.toolboxResult.message ? 620 : 520) : (jarvisBackend.toolboxResult.text ? 600 : 440))
        modal: true
        focus: true
        padding: 0
        closePolicy: Popup.CloseOnEscape

        property var util: ({})

        function openFor(u) {
            util = u
            jarvisBackend.clearToolboxResult()
            for (var i = 0; i < formRepeater.count; i++) {
                var item = formRepeater.itemAt(i)
                if (item && item.resetField) item.resetField()
            }
            open()
        }
        function collectAndRun() {
            var params = {}
            for (var i = 0; i < formRepeater.count; i++) {
                var item = formRepeater.itemAt(i)
                if (item) params[item.fkey] = item.fval
            }
            jarvisBackend.runUtility(utilityDialog.util.id, params)
        }

        onClosed: jarvisBackend.clearToolboxResult()

        Overlay.modal: Rectangle { color: window.isDark ? "#CC020712" : "#80000000" }
        background: Rectangle { radius: 15; color: window.isDark ? "#0A1526" : "#FFFFFF"; border.color: window.isDark ? "#26516A" : "#CBD5E1"; border.width: 1 }

        contentItem: ColumnLayout {
            anchors.fill: parent
            anchors.margins: 22
            spacing: 12

            RowLayout {
                Layout.fillWidth: true
                Column {
                    Layout.fillWidth: true
                    spacing: 2
                    Text { text: (utilityDialog.util.name || "").toUpperCase(); color: cyan; font.pixelSize: 14; font.weight: Font.DemiBold; font.letterSpacing: 1.4 }
                    Text { text: utilityDialog.util.description || ""; color: textMuted; font.pixelSize: 9; wrapMode: Text.Wrap; width: utilityDialog.width - 120 }
                }
                JarvisButton {
                    variant: "close"
                    Layout.preferredWidth: 32
                    Layout.preferredHeight: 32
                    Layout.alignment: Qt.AlignVCenter
                    text: "✕"
                    textSize: 12
                    onClicked: utilityDialog.close()
                }
            }

            Rectangle { Layout.fillWidth: true; height: 1; color: window.isDark ? "#1E3A55" : "#CBD5E1" }

            // aviso de dependencia
            Rectangle {
                visible: utilityDialog.util.available === false
                Layout.fillWidth: true
                Layout.preferredHeight: 64
                radius: 9
                color: window.isDark ? "#3A2A10" : "#FEF3C7"
                border.color: amber
                Text {
                    anchors.fill: parent
                    anchors.margins: 12
                    verticalAlignment: Text.AlignVCenter
                    text: "Instale as bibliotecas extras:\n.\\.venv\\Scripts\\python.exe -m pip install -e \".[tools]\""
                    color: window.isDark ? "#F6D9A0" : "#92400E"; font.pixelSize: 9; font.family: "Consolas, monospace"
                }
            }

            // formulario dinamico
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 10
                visible: utilityDialog.util.available !== false

                Repeater {
                    id: formRepeater
                    model: utilityDialog.util.fields || []

                    delegate: ColumnLayout {
                        id: fieldCol
                        Layout.fillWidth: true
                        spacing: 6
                        property string fkey: modelData.key
                        property var fval: {
                            if (modelData.kind === "files") return multiFilesCol.paths
                            if (modelData.kind === "file") return singleFileRow.path
                            if (choiceBox.visible) return choiceBox.currentText
                            return textBox.text
                        }

                        function resetField() {
                            if (multiFilesCol) multiFilesCol.clear()
                            if (singleFileRow) singleFileRow.path = ""
                            if (textBox) textBox.text = modelData.default || ""
                        }

                        Text { text: modelData.label.toUpperCase(); color: textMuted; font.pixelSize: 8; font.letterSpacing: 1.1 }

                        TextField {
                            id: textBox
                            visible: modelData.kind === "text" || modelData.kind === "int"
                            Layout.fillWidth: true
                            Layout.preferredHeight: visible ? 38 : 0
                            text: modelData.default || ""
                            placeholderText: modelData.placeholder || ""
                            placeholderTextColor: window.isDark ? "#526D83" : "#94A3B8"
                            color: textPrimary; font.pixelSize: 12; leftPadding: 12
                            inputMethodHints: modelData.kind === "int" ? Qt.ImhDigitsOnly : Qt.ImhNone
                            background: Rectangle { radius: 9; color: window.isDark ? "#0D1D33" : "#FFFFFF"; border.color: parent.activeFocus ? cyan : (window.isDark ? "#23435E" : "#CBD5E1") }
                        }

                        FuturisticCombo {
                            id: choiceBox
                            visible: modelData.kind === "choice"
                            Layout.fillWidth: true
                            Layout.preferredHeight: visible ? 38 : 0
                            model: modelData.choices || []
                        }

                        // Campo de arquivo individual
                        RowLayout {
                            id: singleFileRow
                            visible: modelData.kind === "file"
                            Layout.fillWidth: true
                            spacing: 10
                            property string path: ""
                            JarvisButton {
                                text: "📂  ESCOLHER ARQUIVO..."
                                implicitHeight: 36
                                onClicked: {
                                    sharedFileDialog.multi = false
                                    sharedFileDialog.target = singleFileRow
                                    sharedFileDialog.nameFilters = modelData.accept
                                        ? [modelData.accept, "Todos os arquivos (*)"]
                                        : ["Todos os arquivos (*)"]
                                    sharedFileDialog.open()
                                }
                            }
                            Text {
                                Layout.fillWidth: true
                                text: singleFileRow.path ? window.baseName(singleFileRow.path) : "nenhum arquivo selecionado"
                                color: singleFileRow.path ? textPrimary : textMuted
                                font.pixelSize: 11
                                elide: Text.ElideMiddle
                            }
                        }

                        // Campo de múltiplos arquivos com ordenação visual
                        ColumnLayout {
                            id: multiFilesCol
                            visible: modelData.kind === "files"
                            Layout.fillWidth: true
                            spacing: 8

                            property var paths: []

                            function addPaths(newArr) {
                                var copy = paths.slice()
                                for (var i = 0; i < newArr.length; i++) {
                                    var item = newArr[i]
                                    if (copy.indexOf(item) === -1) {
                                        copy.push(item)
                                    }
                                }
                                paths = copy
                            }

                            function moveUp(idx) {
                                if (idx <= 0 || idx >= paths.length) return
                                var copy = paths.slice()
                                var tmp = copy[idx - 1]
                                copy[idx - 1] = copy[idx]
                                copy[idx] = tmp
                                paths = copy
                            }

                            function moveDown(idx) {
                                if (idx < 0 || idx >= paths.length - 1) return
                                var copy = paths.slice()
                                var tmp = copy[idx + 1]
                                copy[idx + 1] = copy[idx]
                                copy[idx] = tmp
                                paths = copy
                            }

                            function removeAt(idx) {
                                if (idx < 0 || idx >= paths.length) return
                                var copy = paths.slice()
                                copy.splice(idx, 1)
                                paths = copy
                            }

                            function clear() {
                                paths = []
                            }

                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 10

                                JarvisButton {
                                    text: "+  ADICIONAR " + (modelData.label ? modelData.label.toUpperCase() : "ARQUIVOS") + "..."
                                    implicitHeight: 36
                                    onClicked: {
                                        sharedFileDialog.multi = true
                                        sharedFileDialog.target = multiFilesCol
                                        sharedFileDialog.nameFilters = modelData.accept
                                            ? [modelData.accept, "Todos os arquivos (*)"]
                                            : ["Todos os arquivos (*)"]
                                        sharedFileDialog.open()
                                    }
                                }

                                JarvisButton {
                                    variant: "danger"
                                    visible: multiFilesCol.paths.length > 0
                                    text: "🗑  LIMPAR"
                                    implicitHeight: 36
                                    textSize: 9
                                    onClicked: multiFilesCol.clear()
                                }

                                Item { Layout.fillWidth: true }

                                Text {
                                    text: multiFilesCol.paths.length === 0
                                          ? "Nenhum arquivo selecionado"
                                          : (multiFilesCol.paths.length + " arquivo(s) na ordem de junção")
                                    color: multiFilesCol.paths.length > 0 ? cyan : textMuted
                                    font.pixelSize: 10
                                    font.weight: Font.DemiBold
                                }
                            }

                            // Lista com a ordem dos arquivos
                            Rectangle {
                                Layout.fillWidth: true
                                Layout.preferredHeight: Math.min(200, Math.max(88, multiFilesCol.paths.length * 44 + 14))
                                radius: 10
                                color: window.isDark ? "#070E1C" : "#F8FAFC"
                                border.color: multiFilesCol.paths.length > 0 ? (window.isDark ? "#1E3B5C" : cyan) : (window.isDark ? "#14253B" : "#CBD5E1")

                                Column {
                                    anchors.centerIn: parent
                                    visible: multiFilesCol.paths.length === 0
                                    spacing: 4
                                    Text {
                                        anchors.horizontalCenter: parent.horizontalCenter
                                        text: "📄  Nenhum arquivo na fila"
                                        color: textMuted
                                        font.pixelSize: 11
                                        font.weight: Font.DemiBold
                                    }
                                    Text {
                                        anchors.horizontalCenter: parent.horizontalCenter
                                        text: "Clique em '+ ADICIONAR...' para selecionar os arquivos e organizar a ordem."
                                        color: window.isDark ? "#526D83" : "#94A3B8"
                                        font.pixelSize: 9
                                    }
                                }

                                ScrollView {
                                    anchors.fill: parent
                                    anchors.margins: 6
                                    clip: true
                                    visible: multiFilesCol.paths.length > 0

                                    ListView {
                                        id: filesListView
                                        width: parent.width
                                        spacing: 5
                                        model: multiFilesCol.paths

                                        delegate: Rectangle {
                                            width: filesListView.width
                                            height: 38
                                            radius: 8
                                            color: itemMouse.containsMouse ? (window.isDark ? "#122A42" : "#E0F2FE") : (window.isDark ? "#0A172B" : "#FFFFFF")
                                            border.color: itemMouse.containsMouse ? cyan : (window.isDark ? "#18324F" : "#CBD5E1")

                                            RowLayout {
                                                anchors.fill: parent
                                                anchors.leftMargin: 10
                                                anchors.rightMargin: 8
                                                spacing: 8

                                                // Badge com ordem de junção
                                                Rectangle {
                                                    width: 22; height: 22
                                                    radius: 11
                                                    color: window.isDark ? "#0F2E47" : "#E0F2FE"
                                                    border.color: cyan
                                                    border.width: 1
                                                    Text {
                                                        anchors.centerIn: parent
                                                        text: "" + (index + 1)
                                                        color: cyan
                                                        font.pixelSize: 10
                                                        font.weight: Font.DemiBold
                                                    }
                                                }

                                                Text {
                                                    text: "📄"
                                                    font.pixelSize: 13
                                                }

                                                Text {
                                                    Layout.fillWidth: true
                                                    text: window.baseName(modelData)
                                                    color: textPrimary
                                                    font.pixelSize: 11
                                                    font.weight: Font.Medium
                                                    elide: Text.ElideMiddle
                                                    ToolTip.visible: itemMouse.containsMouse
                                                    ToolTip.text: modelData
                                                    ToolTip.delay: 400
                                                }

                                                // Botão Subir na Ordem ▲
                                                JarvisButton {
                                                    variant: "secondary"
                                                    customRadius: 6
                                                    Layout.preferredWidth: 28
                                                    Layout.preferredHeight: 28
                                                    enabled: index > 0
                                                    text: "▲"
                                                    textSize: 9
                                                    leftPadding: 0; rightPadding: 0
                                                    onClicked: multiFilesCol.moveUp(index)
                                                    ToolTip.visible: hovered
                                                    ToolTip.text: "Mover para cima (mais cedo na junção)"
                                                    ToolTip.delay: 300
                                                }

                                                // Botão Descer na Ordem ▼
                                                JarvisButton {
                                                    variant: "secondary"
                                                    customRadius: 6
                                                    Layout.preferredWidth: 28
                                                    Layout.preferredHeight: 28
                                                    enabled: index < multiFilesCol.paths.length - 1
                                                    text: "▼"
                                                    textSize: 9
                                                    leftPadding: 0; rightPadding: 0
                                                    onClicked: multiFilesCol.moveDown(index)
                                                    ToolTip.visible: hovered
                                                    ToolTip.text: "Mover para baixo (mais tarde na junção)"
                                                    ToolTip.delay: 300
                                                }

                                                // Botão Excluir item ✕
                                                JarvisButton {
                                                    variant: "close"
                                                    customRadius: 6
                                                    Layout.preferredWidth: 28
                                                    Layout.preferredHeight: 28
                                                    text: "✕"
                                                    textSize: 10
                                                    leftPadding: 0; rightPadding: 0
                                                    onClicked: multiFilesCol.removeAt(index)
                                                    ToolTip.visible: hovered
                                                    ToolTip.text: "Remover este arquivo da lista"
                                                    ToolTip.delay: 300
                                                }
                                            }

                                            MouseArea {
                                                id: itemMouse
                                                anchors.fill: parent
                                                hoverEnabled: true
                                                acceptedButtons: Qt.NoButton
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }

            Item { Layout.fillHeight: true; visible: !jarvisBackend.toolboxResult.message }

            // resultado
            Rectangle {
                visible: jarvisBackend.toolboxResult.message || jarvisBackend.toolboxBusy
                Layout.fillWidth: true
                Layout.fillHeight: jarvisBackend.toolboxResult.text ? true : false
                Layout.preferredHeight: jarvisBackend.toolboxResult.text ? -1 : 88
                Layout.minimumHeight: 88
                radius: 10
                color: window.isDark ? "#060C1A" : "#F8FAFC"
                border.color: jarvisBackend.toolboxBusy ? cyan
                              : (jarvisBackend.toolboxResult.ok ? (window.isDark ? "#1E5238" : "#16A34A") : (window.isDark ? "#5A2A3A" : "#DC2626"))

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 12
                    spacing: 8

                    Text {
                        Layout.fillWidth: true
                        text: jarvisBackend.toolboxBusy ? "Processando..." : (jarvisBackend.toolboxResult.message || "")
                        color: jarvisBackend.toolboxBusy ? cyan
                               : (jarvisBackend.toolboxResult.ok ? (window.isDark ? "#8FE9BF" : "#15803D") : (window.isDark ? "#FF9AAE" : "#DC2626"))
                        font.pixelSize: 10
                        wrapMode: Text.Wrap
                    }

                    ScrollView {
                        visible: !!jarvisBackend.toolboxResult.text
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        TextArea {
                            readOnly: true
                            text: jarvisBackend.toolboxResult.text || ""
                            color: textPrimary; font.pixelSize: 10; wrapMode: TextArea.Wrap
                            background: null; selectByMouse: true
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 8
                        visible: !jarvisBackend.toolboxBusy && jarvisBackend.toolboxResult.ok
                        JarvisButton {
                            variant: "secondary"
                            visible: !!jarvisBackend.toolboxResult.text
                            text: "⧉  COPIAR"
                            implicitHeight: 32; leftPadding: 12; rightPadding: 12; textSize: 9
                            onClicked: jarvisBackend.copyText(jarvisBackend.toolboxResult.text)
                        }
                        JarvisButton {
                            visible: !!jarvisBackend.toolboxResult.outputPath
                            text: "▶  ABRIR ARQUIVO"
                            implicitHeight: 32; leftPadding: 12; rightPadding: 12; textSize: 9
                            onClicked: jarvisBackend.openFile(jarvisBackend.toolboxResult.outputPath)
                        }
                        JarvisButton {
                            variant: "secondary"
                            visible: !!(jarvisBackend.toolboxResult.outputPath || jarvisBackend.toolboxResult.outputDir)
                            text: "📂  ABRIR PASTA"
                            implicitHeight: 32; leftPadding: 12; rightPadding: 12; textSize: 9
                            onClicked: jarvisBackend.revealInExplorer(jarvisBackend.toolboxResult.outputDir || jarvisBackend.toolboxResult.outputPath)
                        }
                        Item { Layout.fillWidth: true }
                    }
                }
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 10
                Item { Layout.fillWidth: true }
                JarvisButton {
                    variant: "secondary"
                    width: 110; height: 40; text: "✕  FECHAR"
                    onClicked: utilityDialog.close()
                }
                JarvisButton {
                    variant: "primary"
                    width: 150; height: 40
                    text: jarvisBackend.toolboxBusy ? "..." : "▶  EXECUTAR"
                    enabled: utilityDialog.util.available !== false && !jarvisBackend.toolboxBusy
                    onClicked: utilityDialog.collectAndRun()
                }
            }
        }
    }

    // ===================================================== PREVIA DE ARQUIVO
    Popup {
        id: filePreview
        objectName: "filePreview"
        parent: Overlay.overlay
        anchors.centerIn: parent
        width: Math.min(window.width - 120, 780)
        height: Math.min(window.height - 100, 620)
        modal: true
        focus: true
        padding: 0
        closePolicy: Popup.CloseOnEscape

        property string filePath: ""
        property string fileName: ""
        property var info: ({})

        function show(path, name) {
            filePath = path
            fileName = name
            info = jarvisBackend.previewFile(path)
            open()
        }

        Overlay.modal: Rectangle { color: window.isDark ? "#CC020712" : "#80000000" }
        background: Rectangle { radius: 15; color: window.isDark ? "#0A1526" : "#FFFFFF"; border.color: window.isDark ? "#26516A" : "#CBD5E1"; border.width: 1 }

        contentItem: ColumnLayout {
            anchors.fill: parent
            anchors.margins: 20
            spacing: 12

            RowLayout {
                Layout.fillWidth: true
                Column {
                    Layout.fillWidth: true
                    spacing: 2
                    Text { text: filePreview.fileName; color: textPrimary; font.pixelSize: 14; font.weight: Font.DemiBold; elide: Text.ElideMiddle; width: filePreview.width - 200 }
                    Text { text: filePreview.filePath; color: textMuted; font.pixelSize: 8; elide: Text.ElideMiddle; width: filePreview.width - 200 }
                }
                Item { Layout.fillWidth: true }
                JarvisButton {
                    text: "▶  ABRIR"
                    implicitHeight: 34; leftPadding: 12; rightPadding: 12; textSize: 9
                    onClicked: jarvisBackend.openFile(filePreview.filePath)
                }
                JarvisButton {
                    visible: filePreview.filePath.toLowerCase().indexOf(".pdf") !== -1
                    text: "✏  EDITAR PDF"
                    implicitHeight: 34; leftPadding: 12; rightPadding: 12; textSize: 9
                    onClicked: {
                        var path = filePreview.filePath
                        filePreview.close()
                        pdfEditorDialog.openFor(path)
                    }
                }
                JarvisButton {
                    text: "🤖  PERGUNTAR"
                    implicitHeight: 34; leftPadding: 12; rightPadding: 12; textSize: 9
                    background: Rectangle {
                        radius: 10; clip: true; opacity: jBtn.down ? 0.75 : 1
                        color: jBtn.hovered ? (window.isDark ? "#241B3A" : "#EDE9FE") : (window.isDark ? "#181229" : "#F5F3FF")
                        border.color: violet
                    }
                    contentItem: Text {
                        text: jBtn.text; color: window.isDark ? "#C9B8FF" : "#6D28D9"
                        font.pixelSize: 9; font.weight: Font.DemiBold; font.letterSpacing: 1.1
                        horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter
                    }
                    onClicked: { jarvisBackend.askJarvisAboutFile(filePreview.filePath); filePreview.close() }
                }
                JarvisButton {
                    variant: "close"
                    Layout.preferredWidth: 32
                    Layout.preferredHeight: 32
                    Layout.alignment: Qt.AlignVCenter
                    text: "✕"
                    textSize: 12
                    onClicked: filePreview.close()
                }
            }

            Rectangle { Layout.fillWidth: true; height: 1; color: window.isDark ? "#1E3A55" : "#CBD5E1" }

            // texto
            Rectangle {
                visible: (filePreview.info.kind || "") === "text"
                Layout.fillWidth: true
                Layout.fillHeight: true
                radius: 9
                color: window.isDark ? "#060C1A" : "#F8FAFC"
                border.color: window.isDark ? "#1B355A" : "#CBD5E1"
                ScrollView {
                    anchors.fill: parent
                    anchors.margins: 10
                    clip: true
                    TextArea {
                        readOnly: true
                        text: (filePreview.info.text || "")
                              + ((filePreview.info.truncated) ? "\n\n... (previa truncada)" : "")
                        color: textPrimary
                        font.pixelSize: 11
                        font.family: "Consolas, monospace"
                        wrapMode: TextArea.NoWrap
                        background: null
                        selectByMouse: true
                    }
                }
            }

            // imagem
            Rectangle {
                visible: (filePreview.info.kind || "") === "image"
                Layout.fillWidth: true
                Layout.fillHeight: true
                radius: 9
                color: window.isDark ? "#060C1A" : "#F8FAFC"
                border.color: window.isDark ? "#1B355A" : "#CBD5E1"
                Image {
                    anchors.fill: parent
                    anchors.margins: 12
                    source: filePreview.info.url || ""
                    fillMode: Image.PreserveAspectFit
                    asynchronous: true
                }
            }

            // sem previa
            Rectangle {
                visible: ["text", "image"].indexOf(filePreview.info.kind || "") === -1
                Layout.fillWidth: true
                Layout.fillHeight: true
                radius: 9
                color: window.isDark ? "#060C1A" : "#F8FAFC"
                border.color: window.isDark ? "#1B355A" : "#CBD5E1"
                Column {
                    anchors.centerIn: parent
                    spacing: 8
                    Text { anchors.horizontalCenter: parent.horizontalCenter; text: filesPanel.glyphFor(filePreview.info.kind || "other"); font.pixelSize: 40 }
                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: filePreview.info.error ? filePreview.info.error : "Sem previa para este tipo. Use ABRIR."
                        color: textMuted; font.pixelSize: 11
                    }
                }
            }
        }
    }

    // ===================================================== EDITOR VISUAL DE PDF
    Popup {
        id: pdfEditorDialog
        objectName: "pdfEditorDialog"
        parent: Overlay.overlay
        anchors.centerIn: parent
        width: Math.min(window.width - 40, 1340)
        height: Math.min(window.height - 30, 840)
        modal: true
        focus: true
        padding: 0
        closePolicy: Popup.CloseOnEscape

        property string originalPath: ""
        property string currentPath: ""
        property string currentName: ""
        property var pages: []
        property int currentPageIndex: 0
        property real zoomScale: 1.0
        property string activeMode: "select"  // "select" | "insert_text" | "insert_image" | "redact" | "find_replace" | "ai"
        property string statusMessage: ""
        property bool busy: false
        property string savedPath: ""
        property string savedDir: ""
        property string selectedImagePath: ""
        property var selectedBlock: null

        readonly property var currentPage: (pages && pages.length > currentPageIndex) ? pages[currentPageIndex] : null

        function openFor(path) {
            savedPath = ""
            savedDir = ""
            statusMessage = ""
            busy = false
            selectedImagePath = ""
            selectedBlock = null
            activeMode = "select"
            zoomScale = 1.0

            if (path && path.length > 0) {
                originalPath = path
                currentPath = path
                loadVisualData(path)
            } else {
                pdfEditorFileDialog.open()
            }
            open()
        }

        function loadVisualData(path) {
            busy = true
            statusMessage = "Renderizando páginas do PDF..."
            var res = jarvisBackend.loadVisualPdf(path)
            busy = false
            if (res.ok) {
                currentPath = res.path
                currentName = res.name || window.baseName(path)
                pages = res.pages || []
                currentPageIndex = Math.min(currentPageIndex, Math.max(0, pages.length - 1))
                statusMessage = "PDF visual carregado com sucesso (" + pages.length + " página(s))."
            } else {
                statusMessage = "Erro ao carregar visualização: " + (res.error || "Falha desconhecida.")
            }
        }

        function reloadOriginal() {
            if (originalPath) {
                currentPath = originalPath
                loadVisualData(originalPath)
                statusMessage = "Documento original recarregado."
            }
        }

        function selectPage(idx) {
            if (idx >= 0 && idx < pages.length) {
                currentPageIndex = idx
                selectedBlock = null
            }
        }

        function applyBlockEdit(block, newText, fontSize, colorHex, fillWhite) {
            if (!block) return
            var edit = {
                "page": currentPageIndex + 1,
                "action": "replace_text",
                "x": block.x,
                "y": block.y,
                "width": block.width,
                "height": block.height,
                "new_text": newText,
                "font_size": fontSize > 0 ? fontSize : Math.max(9.0, block.height * 0.75),
                "color": colorHex || "#000000"
            }
            applyEditsList([edit])
        }

        function insertNewTextAt(x, y, text, fontSize, colorHex, fillWhite) {
            if (!text || text.trim().length === 0) return
            var edit = {
                "page": currentPageIndex + 1,
                "action": "insert_text",
                "x": x,
                "y": y,
                "width": Math.max(140.0, text.length * fontSize * 0.6),
                "height": Math.max(22.0, fontSize * 1.4),
                "text": text,
                "font_size": fontSize,
                "color": colorHex || "#000000",
                "fill_white": fillWhite
            }
            applyEditsList([edit])
        }

        function insertImageAt(x, y, imgPath, width, height) {
            if (!imgPath) return
            var edit = {
                "page": currentPageIndex + 1,
                "action": "insert_image",
                "x": x,
                "y": y,
                "width": width || 150,
                "height": height || 90,
                "image_path": imgPath
            }
            applyEditsList([edit])
        }

        function redactAreaAt(x, y, width, height, colorType) {
            var edit = {
                "page": currentPageIndex + 1,
                "action": "redact",
                "x": x,
                "y": y,
                "width": width || 120,
                "height": height || 25,
                "color": colorType || "white"
            }
            applyEditsList([edit])
        }

        function applyEditsList(edits) {
            busy = true
            statusMessage = "Aplicando alterações no documento..."
            var res = jarvisBackend.applyVisualPdfEdits(currentPath, edits, "")
            busy = false
            if (res.ok) {
                currentPath = res.outputPath || currentPath
                savedPath = res.outputPath || currentPath
                savedDir = res.outputDir || ""
                pages = res.pages || pages
                statusMessage = "✔ " + (res.message || "Alterações aplicadas com sucesso.")
            } else {
                statusMessage = "Erro ao aplicar alterações: " + (res.error || "Falha desconhecida.")
            }
        }

        function doFindReplace(findText, replaceText) {
            if (!findText) return
            busy = true
            statusMessage = "Localizando e substituindo termos no PDF..."
            var res = jarvisBackend.findAndReplacePdfText(currentPath, findText, replaceText, "")
            busy = false
            if (res.ok) {
                currentPath = res.outputPath || currentPath
                savedPath = res.outputPath || currentPath
                savedDir = res.outputDir || ""
                pages = res.pages || pages
                statusMessage = "✔ " + (res.message || "Substituição concluída.")
            } else {
                statusMessage = "Erro ao substituir: " + (res.error || "Falha desconhecida.")
            }
        }

        function rotateCurrentPage(angle) {
            busy = true
            statusMessage = "Rotacionando página..."
            var res = jarvisBackend.rotatePdfPage(currentPath, currentPageIndex + 1, angle, "")
            busy = false
            if (res.ok) {
                currentPath = res.outputPath || currentPath
                savedPath = res.outputPath || currentPath
                pages = res.pages || pages
                statusMessage = "✔ Página rotacionada com sucesso."
            }
        }

        function deleteCurrentPage() {
            if (pages.length <= 1) {
                statusMessage = "O PDF possui apenas uma página e não pode ser excluída."
                return
            }
            busy = true
            statusMessage = "Excluindo página..."
            var res = jarvisBackend.deletePdfPage(currentPath, currentPageIndex + 1, "")
            busy = false
            if (res.ok) {
                currentPath = res.outputPath || currentPath
                savedPath = res.outputPath || currentPath
                pages = res.pages || pages
                currentPageIndex = Math.min(currentPageIndex, pages.length - 1)
                statusMessage = "✔ Página excluída com sucesso."
            }
        }

        function askAiForBlock(promptType, blockText) {
            busy = true
            statusMessage = "Consultando Jarvis IA..."
            var res = jarvisBackend.askAiEdit(promptType, blockText)
            busy = false
            return res
        }

        Overlay.modal: Rectangle { color: window.isDark ? "#CC020712" : "#80000000" }
        background: Rectangle { radius: 15; color: window.isDark ? "#08101E" : "#FFFFFF"; border.color: window.isDark ? "#26516A" : "#CBD5E1"; border.width: 1 }

        contentItem: ColumnLayout {
            anchors.fill: parent
            anchors.margins: 16
            spacing: 8

            // 1. Cabeçalho do Editor Visual
            RowLayout {
                Layout.fillWidth: true
                spacing: 10

                Text { text: "📄"; font.pixelSize: 20 }

                Column {
                    Layout.fillWidth: true
                    spacing: 2
                    RowLayout {
                        spacing: 8
                        Text {
                            text: "EDITAR PDF // VISUALIZADOR & EDITOR INTERATIVO"
                            color: cyan
                            font.pixelSize: 14
                            font.weight: Font.DemiBold
                            font.letterSpacing: 1.4
                        }
                        Rectangle {
                            visible: pdfEditorDialog.currentName.length > 0
                            radius: 6
                            color: window.isDark ? "#122A42" : "#E0F2FE"
                            border.color: window.isDark ? "#235072" : "#7DD3FC"
                            implicitHeight: 22
                            implicitWidth: fileNameBadge.implicitWidth + 14
                            Text {
                                id: fileNameBadge
                                anchors.centerIn: parent
                                text: pdfEditorDialog.currentName
                                color: window.isDark ? "#8AE2FF" : "#0369A1"
                                font.pixelSize: 9
                                font.weight: Font.DemiBold
                            }
                        }
                        Rectangle {
                            visible: pdfEditorDialog.pages.length > 0
                            radius: 6
                            color: window.isDark ? "#0F263C" : "#E0F2FE"
                            border.color: cyan
                            implicitHeight: 22
                            implicitWidth: pageBadge.implicitWidth + 14
                            Text {
                                id: pageBadge
                                anchors.centerIn: parent
                                text: "Página " + (pdfEditorDialog.currentPageIndex + 1) + " de " + pdfEditorDialog.pages.length
                                color: cyan
                                font.pixelSize: 9
                                font.weight: Font.DemiBold
                            }
                        }
                    }
                    Text {
                        text: "Visualização original completa: clique em qualquer texto para editar, insira imagens, tarjas e substitua dados no PDF real."
                        color: textMuted
                        font.pixelSize: 9
                    }
                }

                JarvisButton {
                    variant: "secondary"
                    text: "⟲  RECARREGAR ORIGINAL"
                    implicitHeight: 32; leftPadding: 10; rightPadding: 10; textSize: 8
                    onClicked: pdfEditorDialog.reloadOriginal()
                }

                JarvisButton {
                    text: "📂  CARREGAR OUTRO PDF..."
                    implicitHeight: 32; leftPadding: 10; rightPadding: 10; textSize: 9
                    onClicked: pdfEditorFileDialog.open()
                }

                JarvisButton {
                    variant: "close"
                    Layout.preferredWidth: 32
                    Layout.preferredHeight: 32
                    Layout.alignment: Qt.AlignVCenter
                    text: "✕"
                    textSize: 12
                    onClicked: pdfEditorDialog.close()
                }
            }

            Rectangle { Layout.fillWidth: true; height: 1; color: window.isDark ? "#193552" : "#CBD5E1" }

            // 2. Barra de Modos de Edição + Zoom
            Rectangle {
                Layout.fillWidth: true
                implicitHeight: 44
                radius: 8
                color: window.isDark ? "#070E1C" : "#F8FAFC"
                border.color: window.isDark ? "#18324F" : "#CBD5E1"

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 8
                    anchors.rightMargin: 8
                    spacing: 6

                    // Modo 1: Selecionar e Editar Texto
                    JarvisButton {
                        variant: pdfEditorDialog.activeMode === "select" ? "primary" : "secondary"
                        customRadius: 6
                        implicitHeight: 30; leftPadding: 10; rightPadding: 10; textSize: 8
                        text: "✍  EDITAR TEXTO EXISTENTE"
                        onClicked: pdfEditorDialog.activeMode = "select"
                        ToolTip.visible: hovered; ToolTip.text: "Passe o mouse e clique sobre qualquer texto do PDF para editar"; ToolTip.delay: 300
                    }

                    // Modo 2: Inserir Novo Texto
                    JarvisButton {
                        variant: pdfEditorDialog.activeMode === "insert_text" ? "primary" : "secondary"
                        customRadius: 6
                        implicitHeight: 30; leftPadding: 10; rightPadding: 10; textSize: 8
                        text: "➕  INSERIR NOVO TEXTO"
                        onClicked: pdfEditorDialog.activeMode = "insert_text"
                        ToolTip.visible: hovered; ToolTip.text: "Clique em qualquer lugar da página para inserir um novo texto"; ToolTip.delay: 300
                    }

                    // Modo 3: Inserir Imagem / Assinatura
                    JarvisButton {
                        variant: pdfEditorDialog.activeMode === "insert_image" ? "primary" : "secondary"
                        customRadius: 6
                        implicitHeight: 30; leftPadding: 10; rightPadding: 10; textSize: 8
                        text: "🖼  INSERIR IMAGEM / ASSINATURA"
                        onClicked: {
                            pdfEditorDialog.activeMode = "insert_image"
                            if (!pdfEditorDialog.selectedImagePath) pdfImageFileDialog.open()
                        }
                        ToolTip.visible: hovered; ToolTip.text: "Escolha uma imagem ou assinatura e clique na página para posicionar"; ToolTip.delay: 300
                    }

                    // Modo 4: Ocultar / Tarja
                    JarvisButton {
                        variant: pdfEditorDialog.activeMode === "redact" ? "primary" : "secondary"
                        customRadius: 6
                        implicitHeight: 30; leftPadding: 10; rightPadding: 10; textSize: 8
                        text: "⬛  OCULTAR / TARJA"
                        onClicked: pdfEditorDialog.activeMode = "redact"
                        ToolTip.visible: hovered; ToolTip.text: "Clique no PDF para aplicar uma tarja branca ou preta sobre dados confidenciais"; ToolTip.delay: 300
                    }

                    // Modo 5: Localizar & Substituir
                    JarvisButton {
                        variant: pdfEditorDialog.activeMode === "find_replace" ? "primary" : "secondary"
                        customRadius: 6
                        implicitHeight: 30; leftPadding: 10; rightPadding: 10; textSize: 8
                        text: "🔍  LOCALIZAR & SUBSTITUIR"
                        onClicked: pdfEditorDialog.activeMode = "find_replace"
                        ToolTip.visible: hovered; ToolTip.text: "Substitua qualquer termo, número ou valor em todo o documento"; ToolTip.delay: 300
                    }

                    Item { Layout.fillWidth: true }

                    // Controles de Zoom
                    Text { text: "ZOOM:"; color: textMuted; font.pixelSize: 8; font.weight: Font.DemiBold }
                    JarvisButton {
                        variant: "secondary"; customRadius: 6; Layout.preferredWidth: 24; Layout.preferredHeight: 24; leftPadding: 0; rightPadding: 0; textSize: 9
                        text: "-"
                        onClicked: pdfEditorDialog.zoomScale = Math.max(0.4, pdfEditorDialog.zoomScale - 0.15)
                    }
                    Text {
                        text: Math.round(pdfEditorDialog.zoomScale * 100) + "%"
                        color: cyan
                        font.pixelSize: 9
                        font.weight: Font.DemiBold
                    }
                    JarvisButton {
                        variant: "secondary"; customRadius: 6; Layout.preferredWidth: 24; Layout.preferredHeight: 24; leftPadding: 0; rightPadding: 0; textSize: 9
                        text: "+"
                        onClicked: pdfEditorDialog.zoomScale = Math.min(2.5, pdfEditorDialog.zoomScale + 0.15)
                    }
                    JarvisButton {
                        variant: "secondary"; customRadius: 6; implicitHeight: 24; leftPadding: 6; rightPadding: 6; textSize: 8
                        text: "100%"
                        onClicked: pdfEditorDialog.zoomScale = 1.0
                    }
                    JarvisButton {
                        variant: "secondary"; customRadius: 6; implicitHeight: 24; leftPadding: 6; rightPadding: 6; textSize: 8
                        text: "Ajustar"
                        onClicked: {
                            if (pdfEditorDialog.currentPage && pdfEditorDialog.currentPage.width > 0) {
                                var availW = canvasScrollView.width - 60
                                pdfEditorDialog.zoomScale = Math.min(1.8, Math.max(0.5, availW / pdfEditorDialog.currentPage.width))
                            }
                        }
                    }
                }
            }

            // 3. Barra de Contexto Dinâmica baseada no Modo Selecionado
            Rectangle {
                Layout.fillWidth: true
                implicitHeight: 38
                radius: 8
                color: window.isDark ? "#081427" : "#F1F5F9"
                border.color: window.isDark ? "#1B3B5E" : "#CBD5E1"

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 10
                    anchors.rightMargin: 10
                    spacing: 8

                    // Contexto: Modo Selecionar e Editar
                    RowLayout {
                        visible: pdfEditorDialog.activeMode === "select"
                        spacing: 8
                        Text {
                            text: "💡 DICA: Passe o cursor sobre o documento. Os blocos de texto ficam destacados; clique sobre qualquer texto para editar."
                            color: window.isDark ? "#8FE9BF" : "#15803D"
                            font.pixelSize: 9
                        }
                    }

                    // Contexto: Inserir Novo Texto
                    RowLayout {
                        visible: pdfEditorDialog.activeMode === "insert_text"
                        spacing: 8
                        Text { text: "Texto a inserir:"; color: textMuted; font.pixelSize: 8; font.weight: Font.DemiBold }
                        TextField {
                            id: newTextInput
                            Layout.preferredWidth: 220
                            Layout.preferredHeight: 26
                            placeholderText: "Digite o texto..."
                            placeholderTextColor: window.isDark ? "#526D83" : "#94A3B8"
                            color: textPrimary; font.pixelSize: 9; leftPadding: 8
                            background: Rectangle { radius: 5; color: window.isDark ? "#0D1D33" : "#FFFFFF"; border.color: parent.activeFocus ? cyan : (window.isDark ? "#23435E" : "#CBD5E1") }
                        }
                        Text { text: "Tam:"; color: textMuted; font.pixelSize: 8 }
                        SpinBox {
                            id: newTextSize
                            from: 8; to: 48; value: 12
                            Layout.preferredWidth: 70; Layout.preferredHeight: 26
                        }
                        Text { text: "Cor:"; color: textMuted; font.pixelSize: 8 }
                        Rectangle {
                            id: colorPreto
                            width: 18; height: 18; radius: 9; color: "#000000"; border.color: newTextColor === "#000000" ? cyan : "#444"
                            property string newTextColor: "#000000"
                            MouseArea { anchors.fill: parent; onClicked: newTextColor = "#000000" }
                        }
                        Rectangle {
                            width: 18; height: 18; radius: 9; color: "#003366"; border.color: colorPreto.newTextColor === "#003366" ? cyan : "#444"
                            MouseArea { anchors.fill: parent; onClicked: colorPreto.newTextColor = "#003366" }
                        }
                        Rectangle {
                            width: 18; height: 18; radius: 9; color: "#990000"; border.color: colorPreto.newTextColor === "#990000" ? cyan : "#444"
                            MouseArea { anchors.fill: parent; onClicked: colorPreto.newTextColor = "#990000" }
                        }
                        CheckBox {
                            id: fillWhiteCheck
                            text: "Fundo Branco"
                            checked: false
                        }
                        Text { text: "👉 Clique no documento onde deseja posicionar"; color: cyan; font.pixelSize: 9 }
                    }

                    // Contexto: Inserir Imagem / Assinatura
                    RowLayout {
                        visible: pdfEditorDialog.activeMode === "insert_image"
                        spacing: 8
                        JarvisButton {
                            variant: "secondary"
                            customRadius: 5
                            implicitHeight: 26; leftPadding: 8; rightPadding: 8; textSize: 8
                            text: "📂 ESCOLHER OUTRA IMAGEM..."
                            onClicked: pdfImageFileDialog.open()
                        }
                        Text {
                            text: pdfEditorDialog.selectedImagePath ? ("Imagem: " + window.baseName(pdfEditorDialog.selectedImagePath)) : "Nenhuma imagem selecionada"
                            color: pdfEditorDialog.selectedImagePath ? cyan : "#FF889B"
                            font.pixelSize: 9
                            elide: Text.ElideMiddle
                            Layout.preferredWidth: 200
                        }
                        Text { text: "👉 Clique no PDF para posicionar a imagem"; color: window.isDark ? "#8FE9BF" : "#15803D"; font.pixelSize: 9 }
                    }

                    // Contexto: Ocultar / Tarja
                    RowLayout {
                        visible: pdfEditorDialog.activeMode === "redact"
                        spacing: 8
                        Text { text: "Cor da Tarja:"; color: textMuted; font.pixelSize: 8 }
                        JarvisButton {
                            id: redactWhiteBtn
                            variant: redactColor === "white" ? "primary" : "secondary"
                            customRadius: 5; implicitHeight: 26; leftPadding: 8; rightPadding: 8; textSize: 8
                            text: "Tarja Branca (Apagar)"
                            property string redactColor: "white"
                            onClicked: redactColor = "white"
                        }
                        JarvisButton {
                            variant: redactWhiteBtn.redactColor === "black" ? "primary" : "secondary"
                            customRadius: 5; implicitHeight: 26; leftPadding: 8; rightPadding: 8; textSize: 8
                            text: "Tarja Preta (Censurar)"
                            onClicked: redactWhiteBtn.redactColor = "black"
                        }
                        Text { text: "👉 Clique sobre o trecho que deseja ocultar"; color: cyan; font.pixelSize: 9 }
                    }

                    // Contexto: Localizar & Substituir
                    RowLayout {
                        visible: pdfEditorDialog.activeMode === "find_replace"
                        spacing: 8
                        TextField {
                            id: vrFindInput
                            Layout.preferredWidth: 160
                            Layout.preferredHeight: 26
                            placeholderText: "Texto a localizar (ex: R$ 3.645,52)..."
                            placeholderTextColor: window.isDark ? "#526D83" : "#94A3B8"
                            color: textPrimary; font.pixelSize: 9; leftPadding: 8
                            background: Rectangle { radius: 5; color: window.isDark ? "#0D1D33" : "#FFFFFF"; border.color: parent.activeFocus ? cyan : (window.isDark ? "#23435E" : "#CBD5E1") }
                        }
                        TextField {
                            id: vrReplaceInput
                            Layout.preferredWidth: 160
                            Layout.preferredHeight: 26
                            placeholderText: "Substituir por (ex: R$ 4.500,00)..."
                            placeholderTextColor: window.isDark ? "#526D83" : "#94A3B8"
                            color: textPrimary; font.pixelSize: 9; leftPadding: 8
                            background: Rectangle { radius: 5; color: window.isDark ? "#0D1D33" : "#FFFFFF"; border.color: parent.activeFocus ? cyan : (window.isDark ? "#23435E" : "#CBD5E1") }
                        }
                        JarvisButton {
                            variant: "primary"
                            customRadius: 5
                            implicitHeight: 26; leftPadding: 10; rightPadding: 10; textSize: 8
                            text: "SUBSTITUIR EM TODAS AS PÁGINAS"
                            onClicked: pdfEditorDialog.doFindReplace(vrFindInput.text, vrReplaceInput.text)
                        }
                    }

                    Item { Layout.fillWidth: true }
                }
            }

            // 4. Área Central: Miniaturas das Páginas + Canvas Interativo do PDF
            RowLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: 10

                // Barra Lateral de Miniaturas das Páginas
                Rectangle {
                    Layout.preferredWidth: 170
                    Layout.fillHeight: true
                    radius: 10
                    color: window.isDark ? "#060D1A" : "#F8FAFC"
                    border.color: window.isDark ? "#18324F" : "#CBD5E1"

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 8
                        spacing: 6

                        RowLayout {
                            Layout.fillWidth: true
                            Text {
                                text: "PÁGINAS (" + pdfEditorDialog.pages.length + ")"
                                color: textMuted
                                font.pixelSize: 9
                                font.weight: Font.DemiBold
                                Layout.fillWidth: true
                            }
                            JarvisButton {
                                variant: "secondary"
                                customRadius: 5
                                Layout.preferredWidth: 22; Layout.preferredHeight: 22; leftPadding: 0; rightPadding: 0
                                text: "⟳"
                                textSize: 10
                                onClicked: pdfEditorDialog.rotateCurrentPage(90)
                                ToolTip.visible: hovered; ToolTip.text: "Girar página atual 90°"; ToolTip.delay: 300
                            }
                            JarvisButton {
                                variant: "close"
                                customRadius: 5
                                Layout.preferredWidth: 22; Layout.preferredHeight: 22; leftPadding: 0; rightPadding: 0
                                text: "🗑"
                                textSize: 9
                                visible: pdfEditorDialog.pages.length > 1
                                onClicked: pdfEditorDialog.deleteCurrentPage()
                                ToolTip.visible: hovered; ToolTip.text: "Excluir página atual"; ToolTip.delay: 300
                            }
                        }

                        Rectangle { Layout.fillWidth: true; height: 1; color: window.isDark ? "#142840" : "#CBD5E1" }

                        ScrollView {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            clip: true

                            ListView {
                                id: thumbnailListView
                                width: parent.width
                                spacing: 8
                                model: pdfEditorDialog.pages

                                delegate: Rectangle {
                                    width: thumbnailListView.width
                                    height: 120
                                    radius: 7
                                    color: pdfEditorDialog.currentPageIndex === index ? (window.isDark ? "#122E4D" : "#E0F2FE")
                                           : (thumbMouse.containsMouse ? (window.isDark ? "#0C1D33" : "#F1F5F9") : (window.isDark ? "#081324" : "#FFFFFF"))
                                    border.color: pdfEditorDialog.currentPageIndex === index ? cyan : (window.isDark ? "#163150" : "#CBD5E1")
                                    border.width: pdfEditorDialog.currentPageIndex === index ? 2 : 1

                                    ColumnLayout {
                                        anchors.fill: parent
                                        anchors.margins: 4
                                        spacing: 2

                                        // Miniatura renderizada real do PDF
                                        Rectangle {
                                            Layout.fillWidth: true
                                            Layout.fillHeight: true
                                            color: "#FFFFFF"
                                            radius: 3
                                            clip: true

                                            Image {
                                                anchors.fill: parent
                                                anchors.margins: 2
                                                source: modelData.image || ""
                                                fillMode: Image.PreserveAspectFit
                                                asynchronous: true
                                            }
                                        }

                                        Text {
                                            Layout.alignment: Qt.AlignHCenter
                                            text: "Página " + (index + 1)
                                            color: pdfEditorDialog.currentPageIndex === index ? cyan : textPrimary
                                            font.pixelSize: 9
                                            font.weight: Font.DemiBold
                                        }
                                    }

                                    MouseArea {
                                        id: thumbMouse
                                        anchors.fill: parent
                                        hoverEnabled: true
                                        onClicked: pdfEditorDialog.selectPage(index)
                                    }
                                }
                            }
                        }
                    }
                }

                // Canvas Principal do PDF
                Rectangle {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    radius: 10
                    color: window.isDark ? "#030711" : "#E2E8F0"
                    border.color: window.isDark ? "#152E4A" : "#CBD5E1"
                    clip: true

                    ScrollView {
                        id: canvasScrollView
                        anchors.fill: parent
                        anchors.margins: 8
                        clip: true

                        Flickable {
                            contentWidth: Math.max(canvasScrollView.width, pdfPageContainer.width + 40)
                            contentHeight: Math.max(canvasScrollView.height, pdfPageContainer.height + 40)

                            Item {
                                id: centerContainer
                                width: Math.max(canvasScrollView.width, pdfPageContainer.width + 40)
                                height: Math.max(canvasScrollView.height, pdfPageContainer.height + 40)

                                // Folha de Papel do PDF Renderizada
                                Rectangle {
                                    id: pdfPageContainer
                                    anchors.centerIn: parent
                                    width: pdfEditorDialog.currentPage ? (pdfEditorDialog.currentPage.width * pdfEditorDialog.zoomScale) : 595
                                    height: pdfEditorDialog.currentPage ? (pdfEditorDialog.currentPage.height * pdfEditorDialog.zoomScale) : 842
                                    color: "#FFFFFF"
                                    radius: 4
                                    border.color: "#386588"
                                    border.width: 1

                                    // Imagem da página real do PDF
                                    Image {
                                        id: pdfPageImage
                                        anchors.fill: parent
                                        source: pdfEditorDialog.currentPage ? pdfEditorDialog.currentPage.image : ""
                                        fillMode: Image.Stretch
                                        asynchronous: true
                                    }

                                    // Camada Interativa de Blocos de Texto
                                    Item {
                                        anchors.fill: parent
                                        visible: pdfEditorDialog.activeMode === "select"

                                        Repeater {
                                            model: (pdfEditorDialog.currentPage && pdfEditorDialog.currentPage.blocks) ? pdfEditorDialog.currentPage.blocks : []

                                            delegate: Rectangle {
                                                x: modelData.x * pdfEditorDialog.zoomScale
                                                y: modelData.y * pdfEditorDialog.zoomScale
                                                width: Math.max(12, modelData.width * pdfEditorDialog.zoomScale)
                                                height: Math.max(10, modelData.height * pdfEditorDialog.zoomScale)
                                                radius: 2
                                                color: blockMouse.containsMouse ? "#3300E5FF" : "transparent"
                                                border.color: blockMouse.containsMouse ? "#00E5FF" : "transparent"
                                                border.width: 1

                                                MouseArea {
                                                    id: blockMouse
                                                    anchors.fill: parent
                                                    hoverEnabled: true
                                                    cursorShape: Qt.PointingHandCursor
                                                    onClicked: textBlockEditorPopup.openForBlock(modelData)
                                                    ToolTip.visible: containsMouse
                                                    ToolTip.text: "Clique para editar: \"" + modelData.text.substring(0, 45) + "...\""
                                                    ToolTip.delay: 200
                                                }
                                            }
                                        }
                                    }

                                    // MouseArea Geral da Página para Ações de Clique
                                    MouseArea {
                                        anchors.fill: parent
                                        enabled: pdfEditorDialog.activeMode !== "select"
                                        cursorShape: Qt.CrossCursor
                                        onClicked: {
                                            var pdfX = mouseX / pdfEditorDialog.zoomScale
                                            var pdfY = mouseY / pdfEditorDialog.zoomScale

                                            if (pdfEditorDialog.activeMode === "insert_text") {
                                                pdfEditorDialog.insertNewTextAt(
                                                    pdfX, pdfY,
                                                    newTextInput.text || "Novo Texto",
                                                    newTextSize.value,
                                                    colorPreto.newTextColor,
                                                    fillWhiteCheck.checked
                                                )
                                            } else if (pdfEditorDialog.activeMode === "insert_image") {
                                                if (pdfEditorDialog.selectedImagePath) {
                                                    pdfEditorDialog.insertImageAt(pdfX, pdfY, pdfEditorDialog.selectedImagePath, 150, 90)
                                                } else {
                                                    pdfImageFileDialog.open()
                                                }
                                            } else if (pdfEditorDialog.activeMode === "redact") {
                                                pdfEditorDialog.redactAreaAt(pdfX, pdfY, 120, 25, redactWhiteBtn.redactColor)
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }

                    // Indicador de Carregamento
                    Rectangle {
                        anchors.fill: parent
                        visible: pdfEditorDialog.busy
                        color: window.isDark ? "#B3030711" : "#B3FFFFFF"
                        radius: 10
                        Column {
                            anchors.centerIn: parent
                            spacing: 8
                            Text {
                                anchors.horizontalCenter: parent.horizontalCenter
                                text: "⚙  PROCESSANDO PDF..."
                                color: cyan
                                font.pixelSize: 13
                                font.weight: Font.DemiBold
                                font.letterSpacing: 1.5
                            }
                            Text {
                                anchors.horizontalCenter: parent.horizontalCenter
                                text: pdfEditorDialog.statusMessage
                                color: textMuted
                                font.pixelSize: 10
                            }
                        }
                    }
                }
            }

            // 5. Rodapé: Status + Botões de Salvamento e Ação
            RowLayout {
                Layout.fillWidth: true
                spacing: 10

                Column {
                    Layout.fillWidth: true
                    spacing: 2
                    Text {
                        text: pdfEditorDialog.statusMessage.length > 0 ? pdfEditorDialog.statusMessage
                              : (pdfEditorDialog.currentName + "  |  " + pdfEditorDialog.pages.length + " página(s)")
                        color: pdfEditorDialog.statusMessage.indexOf("Erro") === 0 ? "#FF889B" : (pdfEditorDialog.statusMessage.indexOf("✔") === 0 ? (window.isDark ? "#8FE9BF" : "#15803D") : textMuted)
                        font.pixelSize: 9
                        font.weight: Font.DemiBold
                        elide: Text.ElideRight
                    }
                }

                JarvisButton {
                    visible: pdfEditorDialog.savedPath.length > 0
                    text: "▶  ABRIR ARQUIVO"
                    implicitHeight: 36; leftPadding: 12; rightPadding: 12; textSize: 9
                    onClicked: jarvisBackend.openFile(pdfEditorDialog.savedPath)
                }

                JarvisButton {
                    variant: "secondary"
                    visible: pdfEditorDialog.savedPath.length > 0 || pdfEditorDialog.savedDir.length > 0
                    text: "📂  ABRIR NA PASTA"
                    implicitHeight: 36; leftPadding: 12; rightPadding: 12; textSize: 9
                    onClicked: jarvisBackend.revealInExplorer(pdfEditorDialog.savedDir || pdfEditorDialog.savedPath)
                }

                JarvisButton {
                    variant: "primary"
                    text: "💾  SALVAR COMO PDF"
                    implicitHeight: 36; leftPadding: 16; rightPadding: 16; textSize: 9
                    onClicked: {
                        if (pdfEditorDialog.currentPath) {
                            jarvisBackend.openFile(pdfEditorDialog.currentPath)
                            pdfEditorDialog.statusMessage = "✔ PDF pronto e salvo em: " + pdfEditorDialog.currentPath
                        }
                    }
                }

                JarvisButton {
                    variant: "secondary"
                    text: "✕  FECHAR"
                    implicitHeight: 36; leftPadding: 14; rightPadding: 14; textSize: 9
                    onClicked: pdfEditorDialog.close()
                }
            }
        }

        // Modal Interna para Edição de Bloco de Texto Específico
        Popup {
            id: textBlockEditorPopup
            parent: Overlay.overlay
            anchors.centerIn: parent
            width: Math.min(window.width - 100, 560)
            height: 380
            modal: true
            focus: true
            padding: 0
            closePolicy: Popup.CloseOnEscape

            property var targetBlock: null

            function openForBlock(block) {
                targetBlock = block
                blockTextInput.text = block ? block.text : ""
                blockFontSizeSpin.value = block ? Math.round(Math.max(8, block.height * 0.75)) : 11
                open()
            }

            Overlay.modal: Rectangle { color: window.isDark ? "#CC020712" : "#80000000" }
            background: Rectangle { radius: 12; color: window.isDark ? "#0A172B" : "#FFFFFF"; border.color: cyan; border.width: 1 }

            contentItem: ColumnLayout {
                anchors.fill: parent
                anchors.margins: 16
                spacing: 10

                RowLayout {
                    Layout.fillWidth: true
                    Text { text: "✍  EDITAR TEXTO NO PDF"; color: cyan; font.pixelSize: 12; font.weight: Font.DemiBold; font.letterSpacing: 1.2 }
                    Item { Layout.fillWidth: true }
                    JarvisButton {
                        variant: "close"
                        Layout.preferredWidth: 26; Layout.preferredHeight: 26; text: "✕"; textSize: 10
                        onClicked: textBlockEditorPopup.close()
                    }
                }

                Rectangle { Layout.fillWidth: true; height: 1; color: window.isDark ? "#1B3A5A" : "#CBD5E1" }

                Text { text: "CONTEÚDO DO TEXTO:"; color: textMuted; font.pixelSize: 8; font.weight: Font.DemiBold }

                Rectangle {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    radius: 8
                    color: window.isDark ? "#050C17" : "#F8FAFC"
                    border.color: window.isDark ? "#1A3554" : "#CBD5E1"

                    ScrollView {
                        anchors.fill: parent
                        anchors.margins: 6
                        clip: true

                        TextArea {
                            id: blockTextInput
                            color: textPrimary
                            font.pixelSize: 11
                            font.family: "Consolas, monospace"
                            wrapMode: TextArea.Wrap
                            selectByMouse: true
                            background: null
                        }
                    }
                }

                // Opções de Estilização
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8

                    Text { text: "Tamanho:"; color: textMuted; font.pixelSize: 8 }
                    SpinBox {
                        id: blockFontSizeSpin
                        from: 6; to: 48; value: 11
                        Layout.preferredWidth: 70; Layout.preferredHeight: 28
                    }

                    Text { text: "Cor:"; color: textMuted; font.pixelSize: 8 }
                    Rectangle {
                        id: blockColorBtn
                        width: 20; height: 20; radius: 10; color: "#000000"; border.color: selectedColor === "#000000" ? cyan : "#444"
                        property string selectedColor: "#000000"
                        MouseArea { anchors.fill: parent; onClicked: blockColorBtn.selectedColor = "#000000" }
                    }
                    Rectangle {
                        width: 20; height: 20; radius: 10; color: "#003366"; border.color: blockColorBtn.selectedColor === "#003366" ? cyan : "#444"
                        MouseArea { anchors.fill: parent; onClicked: blockColorBtn.selectedColor = "#003366" }
                    }
                    Rectangle {
                        width: 20; height: 20; radius: 10; color: "#990000"; border.color: blockColorBtn.selectedColor === "#990000" ? cyan : "#444"
                        MouseArea { anchors.fill: parent; onClicked: blockColorBtn.selectedColor = "#990000" }
                    }
                    Rectangle {
                        width: 20; height: 20; radius: 10; color: "#00E5FF"; border.color: blockColorBtn.selectedColor === "#00E5FF" ? cyan : "#444"
                        MouseArea { anchors.fill: parent; onClicked: blockColorBtn.selectedColor = "#00E5FF" }
                    }

                    Item { Layout.fillWidth: true }

                    JarvisButton {
                        text: "🤖 IA APRIMORAR"
                        implicitHeight: 28; leftPadding: 8; rightPadding: 8; textSize: 8
                        background: Rectangle {
                            radius: 6; clip: true; opacity: jBtn.down ? 0.75 : 1
                            color: jBtn.hovered ? (window.isDark ? "#241B3A" : "#EDE9FE") : (window.isDark ? "#181229" : "#F5F3FF"); border.color: violet
                        }
                        contentItem: Text {
                            text: jBtn.text; color: window.isDark ? "#C9B8FF" : "#6D28D9"; font.pixelSize: 8; font.weight: Font.DemiBold
                            horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter
                        }
                        onClicked: {
                            var improved = pdfEditorDialog.askAiForBlock("improve", blockTextInput.text)
                            if (improved && improved.indexOf("Erro") !== 0) blockTextInput.text = improved
                        }
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8

                    JarvisButton {
                        variant: "secondary"
                        text: "✕  CANCELAR"
                        implicitHeight: 32; leftPadding: 12; rightPadding: 12; textSize: 8
                        onClicked: textBlockEditorPopup.close()
                    }

                    Item { Layout.fillWidth: true }

                    JarvisButton {
                        variant: "primary"
                        text: "✔  APLICAR NO PDF"
                        implicitHeight: 32; leftPadding: 14; rightPadding: 14; textSize: 8
                        onClicked: {
                            textBlockEditorPopup.close()
                            pdfEditorDialog.applyBlockEdit(
                                textBlockEditorPopup.targetBlock,
                                blockTextInput.text,
                                blockFontSizeSpin.value,
                                blockColorBtn.selectedColor,
                                true
                            )
                        }
                    }
                }
            }
        }
    }

    // =================================================== NOTIFICAÇÃO DE COMPROMISSO
    Popup {
        id: notifyDialog
        objectName: "notifyDialog"
        parent: Overlay.overlay
        anchors.centerIn: parent
        width: Math.min(window.width - 160, 500)
        height: Math.min(window.height - 80, 360)
        modal: true
        focus: true
        padding: 0
        closePolicy: Popup.NoAutoClose  // só fecha no botão FECHAR

        property var queue: []
        property var current: ({})
        property var snoozed: null

        Timer {
            id: snoozeTimer
            interval: 300000
            onTriggered: {
                if (notifyDialog.snoozed) {
                    notifyDialog.push(notifyDialog.snoozed)
                    notifyDialog.snoozed = null
                }
            }
        }

        function push(info) {
            queue.push(info)
            if (!visible)
                next()
        }
        function next() {
            if (queue.length === 0) { close(); return }
            current = queue.shift()
            open()
        }
        function snooze() {
            snoozed = current
            snoozeTimer.restart()
            next()
        }

        Overlay.modal: Rectangle { color: window.isDark ? "#E6020712" : "#80000000" }
        background: Rectangle {
            radius: 16
            color: window.isDark ? "#0A1730" : "#FFFFFF"
            border.color: cyan
            border.width: 1
        }

        contentItem: ColumnLayout {
            id: notifyCol
            anchors.fill: parent
            anchors.margins: 22
            spacing: 12

            RowLayout {
                Layout.fillWidth: true
                spacing: 10
                Rectangle {
                    width: 34; height: 34; radius: 17
                    color: window.isDark ? "#10344A" : "#E0F2FE"
                    Text { anchors.centerIn: parent; text: "🔔"; font.pixelSize: 16 }
                    SequentialAnimation on scale {
                        loops: Animation.Infinite
                        NumberAnimation { to: 1.12; duration: 500; easing.type: Easing.InOutSine }
                        NumberAnimation { to: 1.0; duration: 500; easing.type: Easing.InOutSine }
                    }
                }
                Column {
                    Layout.fillWidth: true
                    Text { text: "LEMBRETE DE COMPROMISSO"; color: cyan; font.pixelSize: 10; font.weight: Font.DemiBold; font.letterSpacing: 1.4 }
                    Text { text: notifyDialog.queue.length > 0 ? ("+" + notifyDialog.queue.length + " na fila") : ""; color: textMuted; font.pixelSize: 8 }
                }
            }

            Text {
                Layout.fillWidth: true
                text: notifyDialog.current.title || "Compromisso"
                color: textPrimary
                font.pixelSize: 18
                font.weight: Font.DemiBold
                wrapMode: Text.Wrap
            }

            Rectangle { Layout.fillWidth: true; height: 1; color: window.isDark ? "#1E3A55" : "#CBD5E1" }

            GridLayout {
                Layout.fillWidth: true
                columns: 2
                columnSpacing: 14
                rowSpacing: 7

                Text { text: "QUANDO"; color: textMuted; font.pixelSize: 8; font.letterSpacing: 1 }
                Text { text: (notifyDialog.current.whenText || "") ; color: textPrimary; font.pixelSize: 12; Layout.fillWidth: true }

                Text { visible: (notifyDialog.current.location || "").length > 0; text: "LOCAL"; color: textMuted; font.pixelSize: 8; font.letterSpacing: 1 }
                Text { visible: (notifyDialog.current.location || "").length > 0; text: notifyDialog.current.location || ""; color: textPrimary; font.pixelSize: 12; Layout.fillWidth: true }

                Text { visible: (notifyDialog.current.contact || "").length > 0; text: "CONTATO"; color: textMuted; font.pixelSize: 8; font.letterSpacing: 1 }
                Text { visible: (notifyDialog.current.contact || "").length > 0; text: notifyDialog.current.contact || ""; color: textPrimary; font.pixelSize: 12; Layout.fillWidth: true }
            }

            Text {
                visible: (notifyDialog.current.notes || "").length > 0
                Layout.fillWidth: true
                text: notifyDialog.current.notes || ""
                color: textMuted
                font.pixelSize: 10
                wrapMode: Text.Wrap
            }

            Item { Layout.fillHeight: true }

            RowLayout {
                Layout.fillWidth: true
                spacing: 10
                JarvisButton {
                    variant: "secondary"
                    text: "⏰  ADIAR 5 MIN"
                    implicitHeight: 40; textSize: 9
                    onClicked: notifyDialog.snooze()
                }
                Item { Layout.fillWidth: true }
                JarvisButton {
                    variant: "primary"
                    text: "✔  FECHAR"
                    implicitHeight: 40; textSize: 10
                    leftPadding: 22; rightPadding: 22
                    onClicked: notifyDialog.next()
                }
            }
        }
    }
}
