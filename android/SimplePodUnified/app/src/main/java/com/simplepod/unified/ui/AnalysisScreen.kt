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
 * ELI5: This is the diagnostic panel with the multimeter.
 *      We hook up to each circuit (conversation) and measure voltage spikes (red flags).
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AnalysisScreen() {
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
    var analysis by remember { mutableStateOf<com.simplepod.unified.llm.LLMClient.AnalysisResult?>(null) }
    var isLoading by remember { mutableStateOf(false) }

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
            text = "📊 Conversation Analysis",
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
        } else {
            if (selectedThread == null) {
                Text(
                    text = "Select a conversation to analyze (${threads.size} threads)",
                    style = MaterialTheme.typography.bodyMedium,
                    modifier = Modifier.padding(vertical = 8.dp)
                )

                LazyColumn(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    items(threads) { thread ->
                        ThreadCard(thread) {
                            selectedThread = thread
                            scope.launch {
                                isLoading = true
                                analysis = smsManager.analyzeThread(thread.threadId)
                                isLoading = false
                            }
                        }
                    }
                }
            } else {
                // Analysis Result View
                Row(verticalAlignment = Alignment.CenterVertically) {
                    IconButton(onClick = {
                        selectedThread = null
                        analysis = null
                    }) {
                        Text("←")
                    }
                    Text(
                        text = selectedThread?.address ?: "",
                        style = MaterialTheme.typography.titleMedium
                    )
                }

                if (isLoading) {
                    CircularProgressIndicator(modifier = Modifier.align(Alignment.CenterHorizontally))
                }

                analysis?.let { result ->
                    AnalysisResultCard(result)
                }
            }
        }
    }
}

@Composable
fun ThreadCard(thread: SMSManager.ThreadSummary, onClick: () -> Unit) {
    ElevatedCard(
        onClick = onClick,
        modifier = Modifier.fillMaxWidth()
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Text(thread.address, fontWeight = FontWeight.Bold)
            Text(thread.snippet, maxLines = 2)
            Text("${thread.messageCount} messages", style = MaterialTheme.typography.bodySmall)
        }
    }
}

@Composable
fun AnalysisResultCard(result: com.simplepod.unified.llm.LLMClient.AnalysisResult) {
    val sentimentColor = when (result.sentiment) {
        "positive" -> MaterialTheme.colorScheme.primary
        "negative" -> MaterialTheme.colorScheme.error
        else -> MaterialTheme.colorScheme.secondary
    }

    LazyColumn(verticalArrangement = Arrangement.spacedBy(12.dp)) {
        item {
            Card(colors = CardDefaults.cardColors(containerColor = sentimentColor.copy(alpha = 0.1f))) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Text("Sentiment: ${result.sentiment.uppercase()}", fontWeight = FontWeight.Bold)
                    Text("Control Score: ${result.controlScore}/10")
                }
            }
        }

        if (result.redFlags.isNotEmpty()) {
            item {
                Card(colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.errorContainer)) {
                    Column(modifier = Modifier.padding(16.dp)) {
                        Text("⚠ Red Flags Detected", fontWeight = FontWeight.Bold)
                        result.redFlags.forEach { flag ->
                            Text("• $flag")
                        }
                    }
                }
            }
        }

        item {
            Card {
                Column(modifier = Modifier.padding(16.dp)) {
                    Text("Summary", fontWeight = FontWeight.Bold)
                    Text(result.summary)
                }
            }
        }

        item {
            Card(colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.tertiaryContainer)) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Text("Recommendation", fontWeight = FontWeight.Bold)
                    Text(result.recommendation)
                }
            }
        }
    }
}
