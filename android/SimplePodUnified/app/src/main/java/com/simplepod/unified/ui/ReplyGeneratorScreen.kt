package com.simplepod.unified.ui

import android.Manifest
import android.content.pm.PackageManager
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.core.content.ContextCompat
import com.simplepod.unified.sms.SMSManager
import kotlinx.coroutines.launch

/**
 * ELI5: This is the auto-drafter that looks at the blueprints
 *      and suggests the exact wire gauge and breaker size you need.
 *      You can copy the suggestion or send it directly.
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ReplyGeneratorScreen() {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    val smsManager = remember { SMSManager(context) }

    var hasPermission by remember {
        mutableStateOf(
            ContextCompat.checkSelfPermission(context, Manifest.permission.READ_SMS) ==
                    PackageManager.PERMISSION_GRANTED
        )
    }

    var threads by remember { mutableStateOf(listOf<SMSManager.ThreadSummary>()) }
    var selectedThread by remember { mutableStateOf<SMSManager.ThreadSummary?>(null) }
    var reply by remember { mutableStateOf<com.simplepod.unified.llm.LLMClient.ReplyResult?>(null) }
    var isLoading by remember { mutableStateOf(false) }
    var tone by remember { mutableStateOf("neutral") }
    var goal by remember { mutableStateOf("de-escalate") }

    val permissionLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { granted ->
        hasPermission = granted
        if (granted) threads = smsManager.getAllThreads()
    }

    LaunchedEffect(hasPermission) {
        if (hasPermission) threads = smsManager.getAllThreads()
    }

    Column(modifier = Modifier.fillMaxSize().padding(16.dp)) {
        Text(
            text = "💬 Reply Generator",
            style = MaterialTheme.typography.headlineSmall,
            color = MaterialTheme.colorScheme.primary
        )

        if (!hasPermission) {
            Button(
                onClick = { permissionLauncher.launch(Manifest.permission.READ_SMS) },
                modifier = Modifier.fillMaxWidth().padding(vertical = 16.dp)
            ) {
                Text("Grant SMS Permission")
            }
        } else if (selectedThread == null) {
            Text("Select a thread:", modifier = Modifier.padding(vertical = 8.dp))
            LazyColumn(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                items(threads) { thread ->
                    ThreadCard(thread) { selectedThread = thread }
                }
            }
        } else {
            // Reply generation UI
            Row(verticalAlignment = Alignment.CenterVertically) {
                IconButton(onClick = { selectedThread = null; reply = null }) {
                    Text("←")
                }
                Text(selectedThread?.address ?: "", fontWeight = FontWeight.Bold)
            }

            // Tone selector
            Text("Tone:", modifier = Modifier.padding(top = 8.dp))
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                listOf("neutral", "friendly", "firm", "concise").forEach { t ->
                    FilterChip(
                        selected = tone == t,
                        onClick = { tone = t },
                        label = { Text(t) }
                    )
                }
            }

            // Goal selector
            Text("Goal:", modifier = Modifier.padding(top = 8.dp))
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                listOf("de-escalate", "clarify", "end-conversation", "apologize").forEach { g ->
                    FilterChip(
                        selected = goal == g,
                        onClick = { goal = g },
                        label = { Text(g) }
                    )
                }
            }

            Button(
                onClick = {
                    scope.launch {
                        isLoading = true
                        reply = smsManager.generateReplyForThread(
                            selectedThread!!.threadId, tone, goal
                        )
                        isLoading = false
                    }
                },
                modifier = Modifier.fillMaxWidth().padding(vertical = 16.dp),
                enabled = !isLoading
            ) {
                Text(if (isLoading) "Generating..." else "Generate Reply")
            }

            if (isLoading) {
                CircularProgressIndicator(modifier = Modifier.align(Alignment.CenterHorizontally))
            }

            reply?.let { result ->
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    colors = CardDefaults.cardColors(
                        containerColor = MaterialTheme.colorScheme.primaryContainer
                    )
                ) {
                    Column(modifier = Modifier.padding(16.dp)) {
                        Text("Suggested Reply:", fontWeight = FontWeight.Bold)
                        Spacer(modifier = Modifier.height(8.dp))
                        Text(result.reply)
                        Spacer(modifier = Modifier.height(8.dp))
                        Text(
                            "Confidence: ${(result.confidence * 100).toInt()}%",
                            style = MaterialTheme.typography.bodySmall
                        )
                    }
                }
            }
        }
    }
}
