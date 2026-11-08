package com.rex.launcher

import android.content.Context
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
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL

private data class LaunchableApp(val label: String, val packageName: String, val icon: Drawable)
private data class ChatMessage(val text: String, val fromUser: Boolean)

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            RexTheme {
                var apps by remember { mutableStateOf<List<LaunchableApp>>(emptyList()) }
                var loading by remember { mutableStateOf(true) }
                LaunchedEffect(Unit) {
                    apps = withContext(Dispatchers.IO) { loadLaunchableApps() }
                    loading = false
                }
                RexApp(
                    apps = apps,
                    loading = loading,
                    onLaunch = { packageName ->
                        packageManager.getLaunchIntentForPackage(packageName)?.let(::startActivity)
                    },
                    onSaveKey = { key -> getSharedPreferences("rex", Context.MODE_PRIVATE).edit().putString("openrouter_key", key).apply() },
                    savedKey = getSharedPreferences("rex", Context.MODE_PRIVATE).getString("openrouter_key", "") ?: ""
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
                LaunchableApp(info.loadLabel(packageManager)?.toString() ?: packageName, packageName, info.loadIcon(packageManager))
            }
            .distinctBy { it.packageName }
            .sortedBy { it.label.lowercase() }
    }
}

@Composable
private fun RexTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = darkColorScheme(
            background = Color(0xFF080B14), surface = Color(0xFF111827),
            primary = Color(0xFF65E7FF), secondary = Color(0xFFB38CFF)
        ), content = content
    )
}

@Composable
private fun RexApp(
    apps: List<LaunchableApp>, loading: Boolean, onLaunch: (String) -> Unit,
    onSaveKey: (String) -> Unit, savedKey: String
) {
    var page by remember { mutableStateOf("Home") }
    Box(Modifier.fillMaxSize().background(Brush.verticalGradient(listOf(Color(0xFF10172A), Color(0xFF080B14), Color(0xFF160F28))))) {
        Column(Modifier.fillMaxSize().padding(horizontal = 18.dp, vertical = 18.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.SpaceBetween, modifier = Modifier.fillMaxWidth()) {
                Column {
                    Text("REX", color = Color(0xFF65E7FF), fontSize = 30.sp, fontWeight = FontWeight.Bold, letterSpacing = 3.sp)
                    Text("YOUR PHONE. YOUR COMMAND.", color = Color(0xFF9AA8C2), fontSize = 9.sp, letterSpacing = 1.5.sp)
                }
                Text("0.2", color = Color(0xFFB38CFF), fontSize = 12.sp)
            }
            Spacer(Modifier.height(18.dp))
            when (page) {
                "Home" -> HomePage(apps, loading, onLaunch) { page = "Apps" }
                "Apps" -> AppsPage(apps, loading, onLaunch)
                else -> AssistantPage(savedKey, onSaveKey)
            }
            Spacer(Modifier.weight(1f))
            NavigationBar(containerColor = Color(0xDD111827), contentColor = Color.White) {
                listOf("Home", "Apps", "Assistant").forEach { item ->
                    NavigationBarItem(
                        selected = page == item, onClick = { page = item },
                        icon = { Text(when(item) { "Home" -> "⌂"; "Apps" -> "▦"; else -> "✦" }, fontSize = 20.sp) },
                        label = { Text(item, fontSize = 11.sp) },
                        colors = NavigationBarItemDefaults.colors(selectedIconColor = Color(0xFF65E7FF), selectedTextColor = Color(0xFF65E7FF), indicatorColor = Color(0xFF26364F))
                    )
                }
            }
        }
    }
}

@Composable
private fun HomePage(apps: List<LaunchableApp>, loading: Boolean, onLaunch: (String) -> Unit, openApps: () -> Unit) {
    Column(Modifier.fillMaxWidth()) {
        Spacer(Modifier.height(18.dp))
        Text("Good day.", color = Color.White, fontSize = 30.sp, fontWeight = FontWeight.SemiBold)
        Text("Your space. Everything in its place.", color = Color(0xFF9AA8C2), fontSize = 13.sp)
        Spacer(Modifier.height(26.dp))
        Text("QUICK LAUNCH", color = Color(0xFF65E7FF), fontWeight = FontWeight.Bold, letterSpacing = 1.5.sp)
        Spacer(Modifier.height(12.dp))
        if (loading) CircularProgressIndicator(color = Color(0xFF65E7FF))
        else {
            val favorites = apps.take(8)
            LazyVerticalGrid(columns = GridCells.Fixed(4), modifier = Modifier.heightIn(max = 250.dp), horizontalArrangement = Arrangement.spacedBy(8.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                items(favorites, key = { it.packageName }) { app -> AppTile(app) { onLaunch(app.packageName) } }
            }
        }
        Spacer(Modifier.height(24.dp))
        Surface(Modifier.fillMaxWidth().clickable(onClick = openApps), shape = RoundedCornerShape(20.dp), color = Color(0xAA182238)) {
            Row(Modifier.padding(18.dp), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.SpaceBetween) {
                Column {
                    Text("All applications", color = Color.White, fontWeight = FontWeight.SemiBold)
                    Text("Browse and search installed apps", color = Color(0xFF9AA8C2), fontSize = 12.sp)
                }
                Text("→", color = Color(0xFF65E7FF), fontSize = 24.sp)
            }
        }
    }
}

@Composable
private fun AppsPage(apps: List<LaunchableApp>, loading: Boolean, onLaunch: (String) -> Unit) {
    var search by remember { mutableStateOf("") }
    val filtered = remember(apps, search) { apps.filter { it.label.contains(search, ignoreCase = true) } }
    Column(Modifier.fillMaxWidth().weight(1f, fill = false)) {
        Text("App drawer", color = Color.White, fontSize = 26.sp, fontWeight = FontWeight.SemiBold)
        Text("${apps.size} installed apps", color = Color(0xFF9AA8C2), fontSize = 12.sp)
        Spacer(Modifier.height(12.dp))
        OutlinedTextField(search, { search = it }, Modifier.fillMaxWidth(), singleLine = true, label = { Text("Search apps") }, shape = RoundedCornerShape(16.dp))
        Spacer(Modifier.height(12.dp))
        if (loading) CircularProgressIndicator(color = Color(0xFF65E7FF))
        else LazyVerticalGrid(columns = GridCells.Adaptive(minSize = 82.dp), modifier = Modifier.weight(1f), contentPadding = PaddingValues(bottom = 12.dp), horizontalArrangement = Arrangement.spacedBy(8.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            items(filtered, key = { it.packageName }) { app -> AppTile(app) { onLaunch(app.packageName) } }
        }
    }
}

@Composable
private fun AppTile(app: LaunchableApp, onClick: () -> Unit) {
    val bitmap = remember(app.packageName) {
        Bitmap.createBitmap(72, 72, Bitmap.Config.ARGB_8888).also { bmp ->
            val canvas = Canvas(bmp); app.icon.setBounds(0, 0, 72, 72); app.icon.draw(canvas)
        }.asImageBitmap()
    }
    Column(Modifier.fillMaxWidth().clickable(onClick = onClick).padding(5.dp), horizontalAlignment = Alignment.CenterHorizontally) {
        Image(bitmap, contentDescription = app.label, modifier = Modifier.size(42.dp))
        Spacer(Modifier.height(5.dp))
        Text(app.label, color = Color.White, fontSize = 10.sp, maxLines = 1, overflow = TextOverflow.Ellipsis)
    }
}

@Composable
private fun AssistantPage(savedKey: String, onSaveKey: (String) -> Unit) {
    var apiKey by remember(savedKey) { mutableStateOf(savedKey) }
    var input by remember { mutableStateOf("") }
    var busy by remember { mutableStateOf(false) }
    var status by remember { mutableStateOf("Connect an OpenRouter API key to chat with REX.") }
    val messages = remember { mutableStateListOf<ChatMessage>() }
    val scope = rememberCoroutineScope()
    Column(Modifier.fillMaxWidth().weight(1f, fill = false)) {
        Text("REX Assistant", color = Color.White, fontSize = 25.sp, fontWeight = FontWeight.SemiBold)
        Text("Your AI companion", color = Color(0xFF9AA8C2), fontSize = 12.sp)
        Spacer(Modifier.height(10.dp))
        OutlinedTextField(apiKey, { apiKey = it }, Modifier.fillMaxWidth(), singleLine = true, label = { Text("OpenRouter API key") }, visualTransformation = PasswordVisualTransformation(), keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Password))
        Row(verticalAlignment = Alignment.CenterVertically) {
            Button(onClick = { onSaveKey(apiKey.trim()); status = "API key saved on this device." }, enabled = apiKey.isNotBlank()) { Text("Save key") }
            Spacer(Modifier.width(10.dp))
            Text(status, color = Color(0xFF9AA8C2), fontSize = 10.sp, modifier = Modifier.weight(1f))
        }
        Spacer(Modifier.height(8.dp))
        LazyColumn(Modifier.weight(1f).fillMaxWidth(), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            items(messages) { message ->
                Surface(color = if (message.fromUser) Color(0xFF26364F) else Color(0xAA182238), shape = RoundedCornerShape(14.dp)) {
                    Text(message.text, color = Color.White, modifier = Modifier.padding(12.dp), fontSize = 13.sp)
                }
            }
        }
        Row(verticalAlignment = Alignment.CenterVertically) {
            OutlinedTextField(input, { input = it }, Modifier.weight(1f), singleLine = true, label = { Text("Message REX") })
            Spacer(Modifier.width(8.dp))
            Button(enabled = !busy && input.isNotBlank() && apiKey.isNotBlank(), onClick = {
                val prompt = input.trim(); input = ""; messages.add(ChatMessage(prompt, true)); busy = true
                scope.launch {
                    val answer = withContext(Dispatchers.IO) { askOpenRouter(apiKey.trim(), messages.filter { it.text != "" }.takeLast(12)) }
                    messages.add(ChatMessage(answer, false)); status = if (answer.startsWith("REX connection error:")) "Connection failed" else "Connected"; busy = false
                }
            }) { Text(if (busy) "…" else "Send") }
        }
        if (busy) Text("REX is thinking…", color = Color(0xFF65E7FF), fontSize = 11.sp)
    }
}

private fun askOpenRouter(key: String, history: List<ChatMessage>): String {
    var connection: HttpURLConnection? = null
    return try {
        connection = (URL("https://openrouter.ai/api/v1/chat/completions").openConnection() as HttpURLConnection).apply {
            requestMethod = "POST"; connectTimeout = 15000; readTimeout = 30000; doOutput = true
            setRequestProperty("Authorization", "Bearer $key")
            setRequestProperty("Content-Type", "application/json")
            setRequestProperty("HTTP-Referer", "https://github.com/lkrkavin/REX-OS")
            setRequestProperty("X-Title", "REX Launcher")
        }
        val jsonMessages = JSONArray().put(JSONObject().put("role", "system").put("content", "You are REX, a helpful, concise Android assistant."))
        history.forEach { jsonMessages.put(JSONObject().put("role", if (it.fromUser) "user" else "assistant").put("content", it.text)) }
        val body = JSONObject().put("model", "openai/gpt-4o-mini").put("messages", jsonMessages).toString()
        connection.outputStream.use { it.write(body.toByteArray(Charsets.UTF_8)) }
        val stream = if (connection.responseCode in 200..299) connection.inputStream else connection.errorStream
        val response = stream.bufferedReader().use { it.readText() }
        if (connection.responseCode !in 200..299) "REX connection error: HTTP ${connection.responseCode} — ${JSONObject(response).optString("error", response)}"
        else JSONObject(response).getJSONArray("choices").getJSONObject(0).getJSONObject("message").optString("content", "No response received.")
    } catch (e: Exception) {
        "REX connection error: ${e.message ?: "Unknown network error"}"
    } finally { connection?.disconnect() }
}
