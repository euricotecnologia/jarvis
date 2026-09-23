import QtQuick
import QtQuick.Layouts

Rectangle {
    id: root
    property string title: ""
    property string primary: "--"
    property string secondary: ""
    property real percent: 0
    property color accent: "#46EAF7"
    property string glyph: ""

    readonly property bool isDarkTheme: typeof window !== "undefined" && window && window.isDark !== undefined ? window.isDark : true

    radius: 14
    color: isDarkTheme ? "#0A1428" : "#FFFFFF"
    border.color: isDarkTheme ? "#152A44" : "#CBD5E1"
    border.width: 1
    implicitHeight: 108

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 15
        spacing: 6

        RowLayout {
            Layout.fillWidth: true
            spacing: 8
            Text {
                text: root.glyph
                color: root.accent
                font.pixelSize: 13
                visible: root.glyph.length > 0
            }
            Text {
                text: root.title
                color: root.isDarkTheme ? "#7893A8" : "#64748B"
                font.pixelSize: 9
                font.weight: Font.DemiBold
                font.letterSpacing: 1.6
            }
            Item { Layout.fillWidth: true }
        }

        Text {
            text: root.primary
            color: root.isDarkTheme ? "#EAFBFF" : "#0F172A"
            font.pixelSize: 21
            font.weight: Font.DemiBold
        }

        Text {
            text: root.secondary
            color: root.isDarkTheme ? "#6E8AA0" : "#475569"
            font.pixelSize: 10
            visible: root.secondary.length > 0
            Layout.fillWidth: true
            elide: Text.ElideRight
        }

        Item { Layout.fillHeight: true }

        Rectangle {
            Layout.fillWidth: true
            height: 4
            radius: 2
            color: root.isDarkTheme ? "#122840" : "#E2E8F0"
            Rectangle {
                width: parent.width * Math.max(0, Math.min(100, root.percent)) / 100
                height: parent.height
                radius: 2
                color: root.accent
                Behavior on width { NumberAnimation { duration: 500; easing.type: Easing.OutCubic } }
            }
        }
    }
}
