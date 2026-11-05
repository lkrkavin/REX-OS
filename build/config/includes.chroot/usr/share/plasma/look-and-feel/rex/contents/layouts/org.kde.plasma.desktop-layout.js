/*
 * REX OS Plasma 5.27 desktop layout.
 * Plasma's Look-and-Feel scripting API must be obtained with getApiVersion(1).
 */
var plasma = getApiVersion(1);

// Start from a clean layout so applying the REX theme does not duplicate panels.
var existingPanels = plasma.panels();
for (var i = 0; i < existingPanels.length; i++) {
    existingPanels[i].remove();
}

// REX top-left launcher.
var topLeft = new plasma.Panel;
topLeft.location = "top";
topLeft.height = 42;
topLeft.length = 190;
topLeft.alignment = "left";
topLeft.addWidget("org.kde.plasma.kickoff");

// REX top-right system status and clock.
var topRight = new plasma.Panel;
topRight.location = "top";
topRight.height = 42;
topRight.length = 270;
topRight.alignment = "right";
topRight.addWidget("org.kde.plasma.systemtray");
topRight.addWidget("org.kde.plasma.digitalclock");

// Centered floating application dock.
var dock = new plasma.Panel;
dock.location = "floating";
dock.height = 58;
dock.length = 560;
dock.alignment = "center";
dock.hiding = "dodgewindows";
dock.addWidget("org.kde.plasma.icontasks");

// Apply the bundled REX wallpaper to each desktop.
var rexDesktops = plasma.desktops();
for (var j = 0; j < rexDesktops.length; j++) {
    rexDesktops[j].wallpaperPlugin = "org.kde.image";
    rexDesktops[j].currentConfigGroup = ["Wallpaper", "org.kde.image", "General"];
    rexDesktops[j].writeConfig(
        "Image",
        "file:///usr/share/wallpapers/rex/contents/images/REX-OS-wallpaper.png"
    );
}
