// SPDX-License-Identifier: MIT
#include <KPackage/Package>
#include <KPackage/PackageLoader>
#include <KPluginMetaData>
#include <QGuiApplication>
#include <QFileInfo>
#include <QImage>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QPluginLoader>
#include <QQmlComponent>
#include <QQmlEngine>
#include <QQmlExtensionPlugin>
#include <QQuickItem>
#include <QQuickWindow>
#include <QSet>
#include <QSignalSpy>
#include <QTextStream>
#include <QTimer>
#include <cmath>
#include <memory>
#include <stdexcept>
#include <unistd.h>

Q_IMPORT_QML_PLUGIN(org_kde_plasmasetup_componentsPlugin)

static void require(bool condition, const QString &message)
{
    if (!condition) {
        throw std::runtime_error(message.toStdString());
    }
}

static std::unique_ptr<QObject> create(QQmlComponent &component)
{
    auto result = std::unique_ptr<QObject>(component.create());
    require(result && !component.isError(), QStringLiteral("QML creation failed: ") + component.errorString());
    // Confirm the real upstream class, without including its private C++ header.
    require(QString::fromLatin1(result->metaObject()->className()).contains(QStringLiteral("SetupModule")),
            QStringLiteral("root is not the upstream SetupModule"));
    return result;
}

int main(int argc, char **argv)
{
    if (geteuid() == 0 || (!QFileInfo::exists(QStringLiteral("/run/.containerenv"))
                          && qEnvironmentVariable("RO_HARNESS_DISPOSABLE_VM") != QStringLiteral("1"))) {
        QTextStream(stderr) << "FAIL: use an unprivileged container or explicitly disposable VM, never the host desktop\n";
        return 2;
    }
    QGuiApplication app(argc, argv);
    try {
        const QString id = QStringLiteral("org.ro.plasmasetup.development");
        const bool absent = app.arguments().contains(QStringLiteral("--absent"));
        const bool render = app.arguments().contains(QStringLiteral("--render"));
        const auto packages = KPackage::PackageLoader::self()->listKPackages(QStringLiteral("KDE/PlasmaSetup"));
        KPackage::Package sample;
        QJsonArray pages;
        QSet<QString> ids;
        QSet<int> weights;
        for (const auto &package : packages) {
            const auto meta = package.metadata();
            const auto raw = meta.rawData();
            const auto weight = raw.value(QStringLiteral("X-KDE-Weight"));
            require(weight.isDouble() && std::isfinite(weight.toDouble()) && std::floor(weight.toDouble()) == weight.toDouble()
                        && weight.toDouble() >= 0 && weight.toDouble() <= 200,
                    meta.pluginId() + QStringLiteral(": invalid integer weight"));
            const int number = weight.toInt();
            require(!ids.contains(meta.pluginId()), QStringLiteral("duplicate discovered ID: ") + meta.pluginId());
            require(!weights.contains(number), QStringLiteral("duplicate discovered weight: ") + QString::number(number));
            require(package.isValid() && !package.filePath("mainscript").isEmpty(), meta.pluginId() + QStringLiteral(": invalid KPackage/mainscript"));
            require(raw.value(QStringLiteral("X-KDE-ParentApp")) == QStringLiteral("org.kde.plasmasetup"), meta.pluginId() + QStringLiteral(": wrong parent app"));
            ids.insert(meta.pluginId());
            weights.insert(number);
            pages.append(QJsonObject{{"id", meta.pluginId()}, {"weight", number}});
            if (meta.pluginId() == id) {
                sample = package;
            }
        }
        if (absent) {
            require(!ids.contains(id), QStringLiteral("sample still present after removal"));
            QTextStream(stdout) << QJsonDocument(QJsonObject{{"sample_absent", true}, {"pages", pages}}).toJson();
            return 0;
        }
        require(sample.isValid(), QStringLiteral("sample not discovered by Fedora KDE/PlasmaSetup package structure"));
        require(sample.metadata().rawData().value(QStringLiteral("X-KDE-Weight")).toInt() == app.arguments().value(1).toInt(),
                QStringLiteral("wrong discovered sample weight"));
        QQmlEngine engine;
        QQmlComponent component(&engine, QUrl::fromLocalFile(sample.filePath("ui", QStringLiteral("main.qml"))));
        require(component.isReady(), QStringLiteral("QML imports/load failed: ") + component.errorString());

        // Verify upstream defaults with a minimal required contentItem.
        QQmlComponent defaults(&engine);
        defaults.setData("import QtQuick\nimport org.kde.plasmasetup.components\nSetupModule { contentItem: Item {} }", QUrl());
        auto defaultModule = create(defaults);
        require(defaultModule->property("available").toBool() && defaultModule->property("nextEnabled").toBool(),
                QStringLiteral("upstream available/nextEnabled defaults changed"));
        defaultModule.reset();
        QQmlComponent missingContent(&engine);
        missingContent.setData("import org.kde.plasmasetup.components\nSetupModule {}", QUrl());
        std::unique_ptr<QObject> invalid(missingContent.create());
        require(!invalid && missingContent.isError(), QStringLiteral("contentItem is no longer required"));

        QJsonArray instances;
        QQuickWindow window;
        std::unique_ptr<QObject> displayed;
        for (int instance = 0; instance < 2; ++instance) {
            auto module = create(component);
            require(module->property("available").toBool() && !module->property("nextEnabled").toBool(),
                    QStringLiteral("sample state did not reset on creation"));
            auto *content = module->property("contentItem").value<QQuickItem *>();
            require(content && content->objectName() == QStringLiteral("ro-development-content"), QStringLiteral("contentItem not provided"));
            auto *checkBox = content->findChild<QObject *>(QStringLiteral("ro-development-confirmation"));
            require(checkBox && !checkBox->property("checked").toBool(), QStringLiteral("confirmation not reset"));
            QSignalSpy available(module.get(), SIGNAL(availableChanged()));
            QSignalSpy next(module.get(), SIGNAL(nextEnabledChanged()));
            QSignalSpy item(module.get(), SIGNAL(contentItemChanged()));
            require(available.isValid() && next.isValid() && item.isValid(), QStringLiteral("missing public notify signals"));
            require(module->setProperty("available", false) && !module->property("available").toBool(), QStringLiteral("available false failed"));
            module->setProperty("available", true);
            module->setProperty("available", true);
            require(available.count() == 2, QStringLiteral("available signal/value contract failed"));
            checkBox->setProperty("checked", true);
            require(module->property("nextEnabled").toBool(), QStringLiteral("nextEnabled did not follow confirmation"));
            checkBox->setProperty("checked", false);
            require(!module->property("nextEnabled").toBool() && next.count() == 2, QStringLiteral("nextEnabled reset/notify failed"));
            QQuickItem replacement;
            require(module->setProperty("contentItem", QVariant::fromValue(&replacement)), QStringLiteral("contentItem write failed"));
            require(module->property("contentItem").value<QQuickItem *>() == &replacement, QStringLiteral("contentItem getter failed"));
            module->setProperty("contentItem", QVariant::fromValue(content));
            module->setProperty("contentItem", QVariant::fromValue(content));
            require(item.count() == 2, QStringLiteral("contentItem signal contract failed"));
            instances.append(QJsonObject{{"available", true}, {"nextEnabled_binding", true}, {"contentItem_required_and_writable", true}, {"notify_signals", true}});
            if (render && instance == 1) {
                content->setParentItem(window.contentItem());
                content->setPosition(QPointF(32, 32));
                content->setSize(QSizeF(576, 296));
                displayed = std::move(module);
            }
            // First instance destroyed here, just like availability probing.
        }
        QJsonObject output{{"status", "passed"}, {"pages", pages}, {"instances", instances}, {"instantiations", 2}};
        if (render) {
            require(QGuiApplication::platformName() == QStringLiteral("wayland") || QGuiApplication::platformName() == QStringLiteral("xcb"),
                    QStringLiteral("graphical mode requires a real VM Wayland/X11 display"));
            window.setTitle(QStringLiteral("Ro Plasma Setup development probe"));
            window.resize(640, 360);
            window.setColor(Qt::white);
            window.show();
            bool rendered = false;
            QTimer::singleShot(1500, &app, [&] {
                const QImage frame = window.grabWindow();
                QSet<QRgb> colors;
                for (int y = 0; y < frame.height(); ++y) {
                    for (int x = 0; x < frame.width(); ++x) {
                        colors.insert(frame.pixel(x, y));
                    }
                }
                rendered = window.isExposed() && !frame.isNull() && colors.size() > 16;
                const auto renderArgument = app.arguments().indexOf(QStringLiteral("--render"));
                rendered = rendered && frame.save(app.arguments().value(renderArgument + 1));
                output.insert(QStringLiteral("render"), QJsonObject{{"frame_width", frame.width()}, {"frame_height", frame.height()}, {"distinct_colors", int(colors.size())}});
                app.quit();
            });
            app.exec();
            require(rendered, QStringLiteral("graphical frame missing/blank; rendering unverified"));
            // Release visual parent before destroying module/window.
            displayed->property("contentItem").value<QQuickItem *>()->setParentItem(nullptr);
            displayed.reset();
        }
        QTextStream(stdout) << QJsonDocument(output).toJson();
        return 0;
    } catch (const std::exception &error) {
        QTextStream(stderr) << "FAIL: " << error.what() << '\n';
        return 1;
    }
}
