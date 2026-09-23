import QtQuick

Item {
    id: root
    property string mode: "idle"      // idle | listening | thinking | speaking
    property real level: 0            // 0..1 amplitude do microfone
    property color cyan: "#46EAF7"
    property color violet: "#8B5CF6"
    property bool isDarkTheme: true

    readonly property bool active: mode !== "idle"
    readonly property color primary: mode === "listening" ? "#FF6B8A"
                                     : mode === "speaking" ? violet : cyan

    // Anel externo girando
    Rectangle {
        anchors.centerIn: parent
        width: Math.min(parent.width, parent.height)
        height: width
        radius: width / 2
        color: "transparent"
        border.color: root.isDarkTheme ? Qt.rgba(0.27, 0.55, 0.7, 0.5) : Qt.rgba(0.02, 0.52, 0.78, 0.35)
        border.width: 1

        Rectangle {
            anchors.horizontalCenter: parent.horizontalCenter
            y: -5
            width: 30; height: 8; radius: 4
            color: root.primary
        }
        Rectangle {
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.bottom: parent.bottom
            anchors.bottomMargin: -5
            width: 16; height: 8; radius: 4
            color: root.violet
        }

        RotationAnimator on rotation {
            from: 0; to: 360
            duration: root.mode === "listening" ? 3600
                      : root.mode === "thinking" ? 5200
                      : root.mode === "speaking" ? 4200 : 22000
            loops: Animation.Infinite
        }
    }

    // Anel de marcadores girando ao contrario
    Item {
        id: ticks
        anchors.centerIn: parent
        width: Math.min(parent.width, parent.height) * 0.84
        height: width

        Repeater {
            model: 44
            Rectangle {
                required property int index
                width: index % 4 === 0 ? 3 : 2
                height: index % 4 === 0 ? 13 : 6
                radius: 1.5
                color: index % 6 === 0 ? root.violet : root.cyan
                opacity: index % 4 === 0 ? 0.85 : (root.isDarkTheme ? 0.32 : 0.5)
                x: ticks.width / 2 + Math.cos(index * Math.PI * 2 / 44) * (ticks.width / 2 - 8) - width / 2
                y: ticks.height / 2 + Math.sin(index * Math.PI * 2 / 44) * (ticks.height / 2 - 8) - height / 2
                rotation: index * (360 / 44) + 90
            }
        }

        RotationAnimator on rotation {
            from: 360; to: 0
            duration: root.active ? 7000 : 30000
            loops: Animation.Infinite
        }
    }

    // Halo pulsante
    Rectangle {
        anchors.centerIn: parent
        width: Math.min(parent.width, parent.height) * 0.62
        height: width
        radius: width / 2
        color: "transparent"
        border.color: root.primary
        border.width: 1
        opacity: 0.3 + root.level * 0.5
        scale: 1.0 + (root.active ? 0.05 : 0.02) + root.level * 0.12
        Behavior on scale { NumberAnimation { duration: 120 } }

        SequentialAnimation on opacity {
            running: root.active
            loops: Animation.Infinite
            NumberAnimation { to: 0.55; duration: 700; easing.type: Easing.InOutSine }
            NumberAnimation { to: 0.2; duration: 700; easing.type: Easing.InOutSine }
        }
    }

    // Núcleo
    Rectangle {
        id: core
        anchors.centerIn: parent
        width: Math.min(parent.width, parent.height) * 0.4
        height: width
        radius: width / 2
        gradient: Gradient {
            GradientStop { position: 0.0; color: root.isDarkTheme ? "#7CF6FF" : "#38BDF8" }
            GradientStop { position: 0.5; color: root.isDarkTheme ? "#2A8FC4" : "#0284C7" }
            GradientStop { position: 1.0; color: root.mode === "speaking" ? (root.isDarkTheme ? "#6B3FC4" : "#7C3AED") : (root.isDarkTheme ? "#245BAF" : "#0369A1") }
        }

        SequentialAnimation on scale {
            loops: Animation.Infinite
            running: true
            NumberAnimation {
                to: root.active ? 1.09 : 1.03
                duration: root.mode === "speaking" ? 360 : root.active ? 520 : 1900
                easing.type: Easing.InOutSine
            }
            NumberAnimation {
                to: 0.95
                duration: root.mode === "speaking" ? 360 : root.active ? 520 : 1900
                easing.type: Easing.InOutSine
            }
        }

        Rectangle {
            anchors.centerIn: parent
            width: parent.width * 0.42
            height: width
            radius: width / 2
            color: "white"
            opacity: 0.85
        }
    }

    // Ondas concentricas quando fala / ouve
    Repeater {
        model: 3
        Rectangle {
            required property int index
            anchors.centerIn: parent
            width: Math.min(root.width, root.height) * 0.4
            height: width
            radius: width / 2
            color: "transparent"
            border.color: root.primary
            border.width: 1
            visible: root.active
            SequentialAnimation on scale {
                running: root.active
                loops: Animation.Infinite
                PauseAnimation { duration: index * 620 }
                NumberAnimation { from: 1.0; to: 2.4; duration: 1860; easing.type: Easing.OutCubic }
            }
            SequentialAnimation on opacity {
                running: root.active
                loops: Animation.Infinite
                PauseAnimation { duration: index * 620 }
                NumberAnimation { from: 0.5; to: 0.0; duration: 1860; easing.type: Easing.OutCubic }
            }
        }
    }

    Text {
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.top: parent.bottom
        anchors.topMargin: -6
        text: root.mode === "listening" ? "OUVINDO"
              : root.mode === "thinking" ? "PROCESSANDO"
              : root.mode === "speaking" ? "RESPONDENDO" : "NÚCLEO ATIVO"
        color: root.primary
        font.pixelSize: 9
        font.weight: Font.DemiBold
        font.letterSpacing: 2
    }
}
