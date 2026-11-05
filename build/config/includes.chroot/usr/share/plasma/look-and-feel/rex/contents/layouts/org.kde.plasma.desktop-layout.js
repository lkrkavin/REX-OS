/*
 * REX OS Desktop Layout Script for Plasma 5.27
 * Creates a simple REX desktop panel using the Plasma scripting API.
 *
 * Do not use a global "plasma" object here: it is not provided by
 * the Plasma Look-and-Feel layout scripting environment.
 */

// Create a bottom panel with the standard application launcher,
// task manager, system tray and clock.
var panel = new Panel;
panel.location = "bottom";
panel.height = 44;
panel.addWidget("org.kde.plasma.kickoff");
panel.addWidget("org.kde.plasma.taskmanager");
panel.addWidget("org.kde.plasma.systemtray");
panel.addWidget("org.kde.plasma.digitalclock");
