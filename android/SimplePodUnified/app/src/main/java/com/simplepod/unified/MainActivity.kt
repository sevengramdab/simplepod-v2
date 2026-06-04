package com.simplepod.unified

import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.provider.Settings
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import com.simplepod.unified.overlay.ChatHeadService
import com.simplepod.unified.ui.*

/**
 * ELI5: This is the main electrical panel in the basement.
 *      Every switch, every breaker, every display is controlled from here.
 */
class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            SimplePodApp()
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SimplePodApp() {
    val navController = rememberNavController()
    val context = LocalContext.current

    MaterialTheme(
        colorScheme = darkColorScheme(
            primary = MaterialTheme.colorScheme.primary,
            surface = MaterialTheme.colorScheme.surface,
        )
    ) {
        Scaffold(
            topBar = {
                TopAppBar(
                    title = { Text("SimplePod Unified") },
                    colors = TopAppBarDefaults.topAppBarColors(
                        containerColor = MaterialTheme.colorScheme.surfaceVariant
                    )
                )
            }
        ) { padding ->
            NavHost(
                navController = navController,
                startDestination = "main",
                modifier = Modifier.padding(padding)
            ) {
                composable("main") { MainScreen(navController) }
                composable("analysis") { AnalysisScreen() }
                composable("reply") { ReplyGeneratorScreen() }
                composable("swarm") { SwarmStatusScreen() }
                composable("orbitscribe") { OrbitScribeScreen() }
            }
        }
    }
}

@Composable
fun MainScreen(navController: androidx.navigation.NavController) {
    val context = LocalContext.current

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        Text(
            text = "SimplePod Unified Control",
            style = MaterialTheme.typography.headlineMedium,
            color = MaterialTheme.colorScheme.primary
        )

        Text(
            text = "20-Node Swarm | LLM Analysis | MMS Injection",
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )

        Spacer(modifier = Modifier.height(24.dp))

        // ChatHead Toggle
        ActionButton(
            icon = "🖇",
            title = "Floating ChatHead",
            subtitle = "Open/close circle overlay",
            onClick = {
                if (!Settings.canDrawOverlays(context)) {
                    val intent = Intent(
                        Settings.ACTION_MANAGE_OVERLAY_PERMISSION,
                        Uri.parse("package:${context.packageName}")
                    )
                    context.startActivity(intent)
                } else {
                    context.startService(Intent(context, ChatHeadService::class.java))
                }
            }
        )

        ActionButton(
            icon = "📊",
            title = "Conversation Analysis",
            subtitle = "Analyze threads for red flags",
            onClick = { navController.navigate("analysis") }
        )

        ActionButton(
            icon = "💬",
            title = "Reply Generator",
            subtitle = "AI-powered reply suggestions",
            onClick = { navController.navigate("reply") }
        )

        ActionButton(
            icon = "🔗",
            title = "Swarm Status",
            subtitle = "20-worker node monitor",
            onClick = { navController.navigate("swarm") }
        )

        ActionButton(
            icon = "🔭",
            title = "OrbitScribe",
            subtitle = "LLM relationship reasoning",
            onClick = { navController.navigate("orbitscribe") }
        )

        Spacer(modifier = Modifier.weight(1f))

        Text(
            text = "Backend: http://127.0.0.1:8000",
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.outline
        )
    }
}

@Composable
fun ActionButton(
    icon: String,
    title: String,
    subtitle: String,
    onClick: () -> Unit
) {
    ElevatedButton(
        onClick = onClick,
        modifier = Modifier
            .fillMaxWidth()
            .height(72.dp),
        colors = ButtonDefaults.elevatedButtonColors(
            containerColor = MaterialTheme.colorScheme.surfaceVariant
        )
    ) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            Text(text = icon, style = MaterialTheme.typography.headlineMedium)
            Column(modifier = Modifier.weight(1f)) {
                Text(text = title, style = MaterialTheme.typography.titleMedium)
                Text(
                    text = subtitle,
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
            Text(text = "›", style = MaterialTheme.typography.headlineSmall)
        }
    }
}
