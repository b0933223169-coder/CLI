import QtQuick
import QtQuick.Window
import QtWebView

Window {
    width: 900; height: 500
    visible: true
    title: "WebView2 + xterm.js test"
    color: "#1e1e1e"

    WebView {
        id: wv
        anchors.fill: parent
        url: "file:///C:/Users/jusaper/Downloads/coolqml-rs/xterm/index.html"
        Component.onCompleted: console.log("WebView load:", url)
        onLoadingChanged: console.log("loading:", loadRequest.status)
    }
}
