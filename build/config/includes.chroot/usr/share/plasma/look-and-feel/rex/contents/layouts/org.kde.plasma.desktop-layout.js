/*
 * REX OS Desktop Layout Script for Plasma 5.27
 * Configures the top panel and bottom dock
 *
 * Valid APIs: plasma.loadLayout(), plasma.setTheme(), panelIds[]
 * Note: This script reconfigures existing panels from the base layout.
 */

// Load base layout and apply REX theme
plasma.loadLayout('org.kde.plasma.default');
plasma.setTheme('rex');

// Configure Top Panel - exists in org.kde.plasma.default layout
if (panelIds.length > 0) {
    var topPanel = panelIds[0];
    topPanel.location = 'top';

    // Clear widgets
    while (topPanel.widgetIds.length > 0) {
        topPanel.removeWidget(topPanel.widgetIds[0]);
    }

    // Add widgets
    topPanel.addWidget('org.kde.activitymanager');
    topPanel.addWidget('org.kde.systemtray');
    topPanel.addWidget('org.kde.plasma.digitalclock');
    topPanel.addWidget('org.kde.plasma.spacer');
    topPanel.addWidget('org.kde.logout');
}

// Configure Bottom Dock (Panel 1) - exists in org.kde.plasma.default layout
// This may be a dock or panel depending on the default configuration
if (panelIds.length > 1) {
    var dockPanel = panelIds[1];
    dockPanel.location = 'bottom';

    // Clear widgets
    while (dockPanel.widgetIds.length > 0) {
        dockPanel.removeWidget(dockPanel.widgetIds[0]);
    }

    // Add widgets
    dockPanel.addWidget('org.kde.plasma.kickoff');
    dockPanel.addWidget('org.kde.plasma.taskmanager');
    dockPanel.addWidget('org.kde.plasma.spacer');
    dockPanel.addWidget('org.kde.systemtray');
}

// NOTE: If panelIds.length is 1, the bottom dock is not configured
// Users will need to add it manually or through another configuration method