package com.rex.launcher

import android.content.Intent
import android.content.pm.PackageManager
import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.drawable.Drawable
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

private data class LaunchableApp(
    val label: String,
    val packageName: String,
    val icon: Drawable
)

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            RexTheme {
                val apps = remember { loadLaunchableApps() }
                RexHomeScreen(
                    apps = apps,
                    onLaunch = { packageName ->
                        packageManager.getLaunchIntentForPackage(packageName)?.let { launchIntent ->
                            launchIntent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                            startActivity(launchIntent)
                        }
                    }
                )
            }
        }
    }

    @Suppress("DEPRECATION")
    private fun loadLaunchableApps(): List<LaunchableApp> {
        val query = Intent(Intent.ACTION_MAIN).addCategory(Intent.CATEGORY_LAUNCHER)
        return packageManager.queryIntentActivities(query, PackageManager.MATCH_ALL)
            .mapNotNull { info ->
                val activityInfo = info.activityInfo ?: return@mapNotNull null
                val packageName = activityInfo.packageName
                val label = info.loadLabel(packageManager)?.toString() ?: packageName
                LaunchableApp(label, packageName, info.loadIcon(packageManager))
            }
            .distinctBy { it.packageName }
            .sortedBy { it.label.lowercase() }
    }
}

@Composable
private fun RexTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = darkColorScheme(
            background = Color(0xFF080B14),
            surface = Color(0xFF111827),
            primary = Color(0xFF65E7FF),
            secondary = Color(0xFFB38CFF)
        ),
        content = content
    )
}

@Composable
private fun RexHomeScreen(apps: List<LaunchableApp>, onLaunch: (String) -> Unit) {
    var search by remember { mutableStateOf("") }
    val filteredApps = apps.filter { it.label.contains(search, ignoreCase = true) }

    Box(
        modifier = Modifier.fillMaxSize()
            .background(Brush.verticalGradient(
                listOf(Color(0xFF10172A), Color(0xFF080B14), Color(0xFF160F28))
            ))
            .padding(horizontal = 18.dp, vertical = 22.dp)
    ) {
        Column(modifier = Modifier.fillMaxSize()) {
            Text("REX", color = Color(0xFF65E7FF), fontSize = 34.sp,
                fontWeight = FontWeight.Bold, letterSpacing = 3.sp)
            Text("YOUR PHONE. YOUR COMMAND.", color = Color(0xFF9AA8C2),
                fontSize = 10.sp, letterSpacing = 2.sp)
            Spacer(Modifier.height(30.dp))
            Text("Your space.", color = Color.White, fontSize = 27.sp,
                fontWeight = FontWeight.SemiBold)
            Text("Everything you need, one tap away.",
                color = Color(0xFF9AA8C2), fontSize = 13.sp)
            Spacer(Modifier.height(22.dp))
            OutlinedTextField(
                value = search,
                onValueChange = { search = it },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true,
                label = { Text("Search apps") },
                shape = RoundedCornerShape(18.dp)
            )
            Spacer(Modifier.height(18.dp))
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text("APPLICATIONS", color = Color(0xFF65E7FF),
                    fontWeight = FontWeight.Bold, letterSpacing = 1.5.sp)
                Text("${filteredApps.size} apps", color = Color(0xFF9AA8C2), fontSize = 12.sp)
            }
            Spacer(Modifier.height(12.dp))
            if (filteredApps.isEmpty()) {
                Text("No matching apps found.", color = Color(0xFF9AA8C2),
                    modifier = Modifier.padding(top = 16.dp))
            } else {
                LazyVerticalGrid(
                    columns = GridCells.Adaptive(minSize = 88.dp),
                    contentPadding = PaddingValues(bottom = 24.dp),
                    horizontalArrangement = Arrangement.spacedBy(10.dp),
                    verticalArrangement = Arrangement.spacedBy(10.dp)
                ) {
                    items(filteredApps, key = { it.packageName }) { app ->
                        AppTile(app = app, onClick = { onLaunch(app.packageName) })
                    }
                }
            }
        }
    }
}

@Composable
private fun AppTile(app: LaunchableApp, onClick: () -> Unit) {
    val iconBitmap = remember(app.packageName) {
        val bitmap = Bitmap.createBitmap(96, 96, Bitmap.Config.ARGB_8888)
        val canvas = Canvas(bitmap)
        app.icon.setBounds(0, 0, canvas.width, canvas.height)
        app.icon.draw(canvas)
        bitmap.asImageBitmap()
    }
    Surface(
        modifier = Modifier.fillMaxWidth().height(104.dp).clickable(onClick = onClick),
        shape = RoundedCornerShape(18.dp),
        color = Color(0xAA182238),
        tonalElevation = 2.dp
    ) {
        Column(
            modifier = Modifier.padding(10.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Center
        ) {
            Image(bitmap = iconBitmap, contentDescription = app.label,
                modifier = Modifier.size(42.dp))
            Spacer(Modifier.height(7.dp))
            Text(app.label, color = Color.White, fontSize = 11.sp,
                maxLines = 1, overflow = TextOverflow.Ellipsis)
        }
    }
}
