import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Templates as T

ComboBox {
    id: control
    implicitHeight: 44
    font.pixelSize: 11
    selectTextByMouse: true

    readonly property bool isDarkTheme: typeof window !== "undefined" && window && window.isDark !== undefined ? window.isDark : true

    delegate: ItemDelegate {
        id: itemDelegate
        required property var model
        required property var modelData
        required property int index
        width: control.width
        height: 38
        highlighted: control.highlightedIndex === index

        onClicked: {
            control.currentIndex = index
            control.activated(index)
            if (control.editable) {
                var val = control.textRole ? model[control.textRole] : modelData
                control.editText = "" + (val !== undefined ? val : "")
            }
            control.popup.close()
        }

        contentItem: RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 12
            anchors.rightMargin: 12
            spacing: 8

            Text {
                Layout.fillWidth: true
                text: control.textRole ? model[control.textRole] : modelData
                color: itemDelegate.highlighted
                       ? (control.isDarkTheme ? "#38BDF8" : "#0284C7")
                       : (control.isDarkTheme ? "#EAFBFF" : "#0F172A")
                font.pixelSize: 11
                font.weight: itemDelegate.highlighted ? Font.DemiBold : Font.Normal
                verticalAlignment: Text.AlignVCenter
                elide: Text.ElideRight
            }

            Text {
                visible: control.currentIndex === itemDelegate.index
                text: "✓"
                color: control.isDarkTheme ? "#38BDF8" : "#0284C7"
                font.pixelSize: 11
                font.weight: Font.Bold
            }
        }

        background: Rectangle {
            color: itemDelegate.highlighted || itemDelegate.hovered
                   ? (control.isDarkTheme ? "#14364C" : "#E0F2FE")
                   : (control.isDarkTheme ? "#0A152A" : "#FFFFFF")
        }
    }

    indicator: Item {
        id: indicatorContainer
        x: control.mirrored ? control.leftPadding : control.width - width - 4
        y: (control.height - height) / 2
        width: 32
        height: control.height
        z: 10

        Rectangle {
            anchors.centerIn: parent
            width: 24
            height: 24
            radius: 6
            color: arrowArea.containsMouse
                   ? (control.isDarkTheme ? "#1E3A5A" : "#E2E8F0")
                   : "transparent"

            Text {
                anchors.centerIn: parent
                text: "▾"
                font.pixelSize: 15
                font.weight: Font.Bold
                color: control.popup.visible
                       ? (control.isDarkTheme ? "#46EAF7" : "#0284C7")
                       : (arrowArea.containsMouse
                           ? (control.isDarkTheme ? "#38BDF8" : "#0284C7")
                           : (control.isDarkTheme ? "#7DD3FC" : "#64748B"))
                rotation: control.popup.visible ? 180 : 0
                Behavior on rotation { NumberAnimation { duration: 150 } }
                Behavior on color { ColorAnimation { duration: 150 } }
            }
        }

        MouseArea {
            id: arrowArea
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: {
                if (control.popup.visible) {
                    control.popup.close()
                } else {
                    control.popup.open()
                }
            }
        }
    }

    contentItem: T.TextField {
        leftPadding: 13
        rightPadding: 38
        text: control.editable ? control.editText : control.displayText
        color: control.isDarkTheme ? "#EAFBFF" : "#0F172A"
        font: control.font
        verticalAlignment: Text.AlignVCenter
        enabled: control.editable
        selectByMouse: control.editable
        autoScroll: control.editable
        readOnly: !control.editable || control.down
        inputMethodHints: control.inputMethodHints
        placeholderText: control.editable && (!text || text.length === 0) ? (control.placeholderText || "digite ou selecione um modelo...") : ""
        placeholderTextColor: control.isDarkTheme ? "#526D83" : "#94A3B8"
        background: null

        onTextEdited: {
            if (control.editable) {
                control.editText = text
            }
        }

        Keys.onDownPressed: {
            if (!control.popup.visible) {
                control.popup.open()
            }
        }
    }

    background: Rectangle {
        radius: 9
        color: control.isDarkTheme
               ? (control.hovered ? "#10233A" : "#0D1D33")
               : (control.hovered ? "#F8FAFC" : "#FFFFFF")
        border.color: (control.activeFocus || control.popup.visible)
                      ? (control.isDarkTheme ? "#46EAF7" : "#0284C7")
                      : (control.isDarkTheme ? "#23435E" : "#CBD5E1")
        border.width: (control.activeFocus || control.popup.visible) ? 1.5 : 1
    }

    popup: Popup {
        y: control.height + 4
        width: control.width
        implicitHeight: Math.min(Math.max(comboListView.contentHeight + 6, 40), 270)
        padding: 2
        z: 9999

        contentItem: ListView {
            id: comboListView
            clip: true
            implicitHeight: contentHeight
            model: control.popup.visible ? control.delegateModel : null
            currentIndex: control.highlightedIndex
            boundsBehavior: Flickable.StopAtBounds
            ScrollIndicator.vertical: ScrollIndicator {
                active: comboListView.contentHeight > 270
            }
        }
        background: Rectangle {
            radius: 9
            color: control.isDarkTheme ? "#0A152A" : "#FFFFFF"
            border.color: control.isDarkTheme ? "#23435E" : "#CBD5E1"
            border.width: 1
        }
    }
}
