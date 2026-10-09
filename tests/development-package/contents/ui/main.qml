// SPDX-License-Identifier: CC0-1.0
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import org.kde.plasmasetup.components as PlasmaSetupComponents

PlasmaSetupComponents.SetupModule {
    id: root
    objectName: "ro-development-module"
    available: true
    nextEnabled: confirmation.checked
    contentItem: ColumnLayout {
        objectName: "ro-development-content"
        spacing: 16

        Label {
            Layout.fillWidth: true
            text: qsTr("Development contract probe")
            font.bold: true
            wrapMode: Text.WordWrap
        }
        Label {
            Layout.fillWidth: true
            text: qsTr("This test page keeps all state in memory.")
            wrapMode: Text.WordWrap
        }
        CheckBox {
            id: confirmation
            objectName: "ro-development-confirmation"
            text: qsTr("Enable Next for this instance")
            checked: false
        }
    }
}
