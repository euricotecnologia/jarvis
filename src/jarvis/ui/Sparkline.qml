import QtQuick

Item {
    id: root
    property real v1: 0
    property real v2: 0
    property real v3: 0
    property color c1: "#46EAF7"
    property color c2: "#8B5CF6"
    property color c3: "#4EF2A6"
    property int points: 40

    property var _b1: []
    property var _b2: []
    property var _b3: []

    readonly property bool isDarkTheme: typeof window !== "undefined" && window && window.isDark !== undefined ? window.isDark : true
    onIsDarkThemeChanged: canvas.requestPaint()

    Component.onCompleted: {
        for (var i = 0; i < points; i++) { _b1.push(0); _b2.push(0); _b3.push(0) }
    }

    Timer {
        interval: 1500
        running: true
        repeat: true
        onTriggered: {
            _b1.push(root.v1); _b1.shift()
            _b2.push(root.v2); _b2.shift()
            _b3.push(root.v3); _b3.shift()
            canvas.requestPaint()
        }
    }

    Canvas {
        id: canvas
        anchors.fill: parent
        onPaint: {
            var ctx = getContext("2d")
            ctx.reset()
            var w = width, h = height

            ctx.strokeStyle = root.isDarkTheme ? "#12233A" : "#E2E8F0"
            ctx.lineWidth = 1
            for (var g = 0; g <= 4; g++) {
                var gy = h * g / 4
                ctx.beginPath(); ctx.moveTo(0, gy); ctx.lineTo(w, gy); ctx.stroke()
            }

            function line(buf, color) {
                if (!buf || buf.length < 2) return
                ctx.beginPath()
                ctx.strokeStyle = color
                ctx.lineWidth = 2
                for (var i = 0; i < buf.length; i++) {
                    var x = w * i / (buf.length - 1)
                    var y = h - h * Math.max(0, Math.min(100, buf[i])) / 100
                    if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y)
                }
                ctx.stroke()
            }

            line(root._b1, root.c1)
            line(root._b2, root.c2)
            line(root._b3, root.c3)
        }
    }
}
