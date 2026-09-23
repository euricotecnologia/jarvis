import QtQuick

Item {
    id: root
    property real value: 0          // 0..100
    property string caption: ""
    property color accent: "#46EAF7"
    property int thickness: 8
    property int fontSize: 26

    readonly property bool isDarkTheme: typeof window !== "undefined" && window && window.isDark !== undefined ? window.isDark : true
    property color track: isDarkTheme ? "#132A3F" : "#E2E8F0"

    implicitWidth: 120
    implicitHeight: 120

    Canvas {
        id: canvas
        anchors.fill: parent
        onPaint: {
            var ctx = getContext("2d")
            ctx.reset()
            var cx = width / 2
            var cy = height / 2
            var r = Math.min(width, height) / 2 - root.thickness
            ctx.lineWidth = root.thickness
            ctx.lineCap = "round"

            ctx.beginPath()
            ctx.strokeStyle = root.track
            ctx.arc(cx, cy, r, 0, Math.PI * 2)
            ctx.stroke()

            var frac = Math.max(0, Math.min(100, root.value)) / 100
            if (frac > 0) {
                ctx.beginPath()
                ctx.strokeStyle = root.accent
                ctx.arc(cx, cy, r, -Math.PI / 2, -Math.PI / 2 + frac * Math.PI * 2)
                ctx.stroke()
            }
        }
    }

    Behavior on value { NumberAnimation { duration: 600; easing.type: Easing.OutCubic } }
    onValueChanged: canvas.requestPaint()
    onAccentChanged: canvas.requestPaint()
    onTrackChanged: canvas.requestPaint()
    onIsDarkThemeChanged: canvas.requestPaint()
    Component.onCompleted: canvas.requestPaint()

    Column {
        anchors.centerIn: parent
        spacing: 2
        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: Math.round(root.value) + "%"
            color: root.isDarkTheme ? "#EAFBFF" : "#0F172A"
            font.pixelSize: root.fontSize
            font.weight: Font.DemiBold
        }
        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            visible: root.caption.length > 0
            text: root.caption
            color: root.isDarkTheme ? "#7893A8" : "#64748B"
            font.pixelSize: 8
            font.letterSpacing: 1.4
        }
    }
}
