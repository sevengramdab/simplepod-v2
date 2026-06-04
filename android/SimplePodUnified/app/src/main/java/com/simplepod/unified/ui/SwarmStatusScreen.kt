package com.simplepod.unified.ui

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.simplepod.unified.llm.LLMClient
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

/**
 * ELI5: This is the main breaker panel status display.
 *      Every circuit (worker) shows green (online), yellow (busy), or red (tripped).
 *      You can see total load, queue depth, and messages processed at a glance.
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SwarmStatusScreen() {
    val scope = rememberCoroutineScope()
    val client = remember { LLMClient() }

    var status by remember { mutableStateOf<LLMClient.SwarmStatus?>(null) }
    var isRefreshing by remember { mutableStateOf(false) }
    var lastError by remember { mutableStateOf<String?>(null) }

    fun refresh() {
        scope.launch {
            isRefreshing = true
            lastError = null
            try {
                status = client.getSwarmStatus()
            } catch (e: Exception) {
                lastError = e.message
            }
            isRefreshing = false
        }
    }

    LaunchedEffect(Unit) {
        refresh()
        while (true) {
            delay(5000) // Auto-refresh every 5 seconds
            refresh()
        }
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text(
                text = "🔗 Swarm Status",
                style = MaterialTheme.typography.headlineSmall,
                color = MaterialTheme.colorScheme.primary
            )
            IconButton(onClick = { refresh() }, enabled = !isRefreshing) {
                Text(if (isRefreshing) "⏳" else "🗘")
            }
        }

        lastError?.let {
            Card(colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.errorContainer)) {
                Text(
                    text = "Error: $it",
                    modifier = Modifier.padding(16.dp),
                    color = MaterialTheme.colorScheme.onErrorContainer
                )
            }
        }

        status?.let { s ->
            // Overall Status Card
            Card(
                modifier = Modifier.fillMaxWidth(),
                colors = CardDefaults.cardColors(
                    containerColor = if (s.running)
                        MaterialTheme.colorScheme.primaryContainer
                    else
                        MaterialTheme.colorScheme.errorContainer
                )
            ) {
                Column(modifier = Modifier.padding(20.dp)) {
                    Text(
                        text = if (s.running) "SWARM ONLINE" else "SWARM OFFLINE",
                        fontWeight = FontWeight.Bold,
                        style = MaterialTheme.typography.titleLarge
                    )
                    Spacer(modifier = Modifier.height(8.dp))
                    StatRow("Active Workers", "${s.activeWorkers} / 20")
                    StatRow("Queue Depth", s.queueDepth.toString())
                    StatRow("Messages Processed", s.messagesProcessed.toString())
                }
            }

            // Worker Grid (visual representation)
            Text("Worker Nodes:", fontWeight = FontWeight.Bold, modifier = Modifier.padding(top = 8.dp))

            val workerStates = remember(s.activeWorkers, s.running) {
                List(20) { i ->
                    when {
                        !s.running -> WorkerState.OFFLINE
                        i < s.activeWorkers -> WorkerState.ACTIVE
                        else -> WorkerState.IDLE
                    }
                }
            }

            // Show workers in a 5x4 grid
            Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                for (row in 0 until 4) {
                    Row(horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                        for (col in 0 until 5) {
                            val idx = row * 5 + col
                            WorkerDot(workerStates[idx], idx + 1)
                        }
                    }
                }
            }

            // Legend
            Row(horizontalArrangement = Arrangement.spacedBy(16.dp), modifier = Modifier.padding(top = 8.dp)) {
                LegendItem("🟢", "Active")
                LegendItem("🟡", "Idle")
                LegendItem("🔴", "Offline")
            }

        } ?: run {
            if (!isRefreshing) {
                Card(modifier = Modifier.fillMaxWidth()) {
                    Text(
                        "No status available. Check backend connection.",
                        modifier = Modifier.padding(16.dp)
                    )
                }
            }
        }

        Spacer(modifier = Modifier.weight(1f))

        // Backend URL indicator
        Text(
            text = "Backend: http://10.0.2.2:8000",
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.outline
        )
    }
}

enum class WorkerState { ACTIVE, IDLE, OFFLINE }

@Composable
fun WorkerDot(state: WorkerState, number: Int) {
    val color = when (state) {
        WorkerState.ACTIVE -> MaterialTheme.colorScheme.primary
        WorkerState.IDLE -> MaterialTheme.colorScheme.secondary.copy(alpha = 0.5f)
        WorkerState.OFFLINE -> MaterialTheme.colorScheme.error.copy(alpha = 0.3f)
    }

    Surface(
        modifier = Modifier.size(32.dp),
        shape = MaterialTheme.shapes.small,
        color = color
    ) {
        Box(contentAlignment = Alignment.Center) {
            Text(
                text = number.toString(),
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onPrimary
            )
        }
    }
}

@Composable
fun StatRow(label: String, value: String) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween
    ) {
        Text(label, style = MaterialTheme.typography.bodyMedium)
        Text(value, fontWeight = FontWeight.Bold)
    }
}

@Composable
fun LegendItem(emoji: String, label: String) {
    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(4.dp)) {
        Text(emoji)
        Text(label, style = MaterialTheme.typography.bodySmall)
    }
}
