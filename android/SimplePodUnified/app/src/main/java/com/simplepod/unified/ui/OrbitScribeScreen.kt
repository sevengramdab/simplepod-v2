package com.simplepod.unified.ui

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.simplepod.unified.llm.LLMClient
import kotlinx.coroutines.launch

/**
 * ELI5: This is the master electrician's full diagnostic report on your phone.
 *      It reads the wiring diagram of every relationship and tells you
 *      where the circuits are overheating, where power is being diverted,
 *      and which breakers are about to trip.
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun OrbitScribeScreen() {
    val scope = rememberCoroutineScope()
    val client = remember { LLMClient() }

    var report by remember { mutableStateOf<OrbitScribeReport?>(null) }
    var isLoading by remember { mutableStateOf(false) }
    var mode by remember { mutableStateOf("synthetic") }

    fun loadReport() {
        scope.launch {
            isLoading = true
            report = client.orbitscribeAnalyze(mode)
            isLoading = false
        }
    }

    LaunchedEffect(Unit) { loadReport() }

    Column(modifier = Modifier.fillMaxSize().padding(16.dp)) {
        Text(
            text = "\uD83D\uDD2D OrbitScribe Relationship Engine",
            style = MaterialTheme.typography.headlineSmall,
            color = MaterialTheme.colorScheme.primary
        )
        Text(
            text = "LLM-powered reasoning with chain-of-thought",
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )

        Spacer(modifier = Modifier.height(12.dp))

        // Mode selector
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            listOf("synthetic" to "\u26A1 Instant", "auto" to "\uD83E\uDD16 Auto", "llm" to "\uD83E\uDDE0 Full LLM").forEach { (m, label) ->
                FilterChip(
                    selected = mode == m,
                    onClick = { mode = m; loadReport() },
                    label = { Text(label) }
                )
            }
        }

        Spacer(modifier = Modifier.height(8.dp))

        Button(
            onClick = { loadReport() },
            modifier = Modifier.fillMaxWidth(),
            enabled = !isLoading
        ) {
            Text(if (isLoading) "Analyzing..." else "Run Analysis")
        }

        if (isLoading) {
            CircularProgressIndicator(modifier = Modifier.align(Alignment.CenterHorizontally).padding(16.dp))
        }

        report?.let { r ->
            LazyColumn(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                // Risk banner
                item {
                    val riskColor = when (r.risk_level) {
                        "critical" -> MaterialTheme.colorScheme.error
                        "high" -> MaterialTheme.colorScheme.tertiary
                        "moderate" -> MaterialTheme.colorScheme.secondary
                        else -> MaterialTheme.colorScheme.primary
                    }
                    Card(colors = CardDefaults.cardColors(containerColor = riskColor.copy(alpha = 0.15f))) {
                        Column(modifier = Modifier.padding(16.dp)) {
                            Text("RISK: ${r.risk_level.uppercase()}", fontWeight = FontWeight.Bold, color = riskColor)
                            Text("Mode: ${r.mode} | LLM: ${if (r.llm_used) "YES" else "NO"}", style = MaterialTheme.typography.bodySmall)
                        }
                    }
                }

                // Narrative
                item {
                    Card {
                        Column(modifier = Modifier.padding(16.dp)) {
                            Text("Narrative", fontWeight = FontWeight.Bold)
                            Spacer(modifier = Modifier.height(8.dp))
                            Text(r.overall_narrative, style = MaterialTheme.typography.bodyMedium)
                        }
                    }
                }

                // Attachments
                item {
                    Text("Attachment Analyses", fontWeight = FontWeight.Bold, modifier = Modifier.padding(top = 8.dp))
                }
                items(r.attachment_analyses) { a ->
                    val styleColor = when (a.attachment_style) {
                        "secure" -> MaterialTheme.colorScheme.primary
                        "anxious" -> MaterialTheme.colorScheme.tertiary
                        "avoidant" -> MaterialTheme.colorScheme.secondary
                        "disorganized" -> MaterialTheme.colorScheme.error
                        else -> MaterialTheme.colorScheme.outline
                    }
                    Card(colors = CardDefaults.cardColors(containerColor = styleColor.copy(alpha = 0.1f))) {
                        Column(modifier = Modifier.padding(16.dp)) {
                            Text("${a.subject} \u2194 ${a.partner}", fontWeight = FontWeight.Bold)
                            Text(a.attachment_style.uppercase(), color = styleColor, fontWeight = FontWeight.Bold)
                            Text("Confidence: ${(a.confidence * 100).toInt()}%", style = MaterialTheme.typography.bodySmall)
                            a.evidence.take(2).forEach { ev ->
                                Text("\"$ev\"", style = MaterialTheme.typography.bodySmall, fontWeight = FontWeight.Light)
                            }
                        }
                    }
                }

                // Triangulations
                item {
                    Text("Triangulation Events", fontWeight = FontWeight.Bold, modifier = Modifier.padding(top = 8.dp))
                }
                items(r.triangulation_events) { t ->
                    val scoreColor = if (t.manipulative_score > 0.7f) MaterialTheme.colorScheme.error else MaterialTheme.colorScheme.tertiary
                    Card(colors = CardDefaults.cardColors(containerColor = scoreColor.copy(alpha = 0.1f))) {
                        Column(modifier = Modifier.padding(16.dp)) {
                            Text("${t.speaker} \u2192 ${t.listener} (about ${t.target})", fontWeight = FontWeight.Bold)
                            Text("Manipulative: ${(t.manipulative_score * 100).toInt()}%", color = scoreColor)
                            Text(t.context, style = MaterialTheme.typography.bodySmall, maxLines = 3)
                        }
                    }
                }

                // Trajectories
                item {
                    Text("Emotional Trajectories", fontWeight = FontWeight.Bold, modifier = Modifier.padding(top = 8.dp))
                }
                items(r.emotional_trajectories) { et ->
                    val trajColor = when (et.trajectory) {
                        "improving" -> MaterialTheme.colorScheme.primary
                        "stable" -> MaterialTheme.colorScheme.secondary
                        "declining" -> MaterialTheme.colorScheme.error
                        "volatile" -> MaterialTheme.colorScheme.tertiary
                        else -> MaterialTheme.colorScheme.outline
                    }
                    Card {
                        Column(modifier = Modifier.padding(16.dp)) {
                            Text(et.thread_id, fontWeight = FontWeight.Bold)
                            Text(et.trajectory.uppercase(), color = trajColor, fontWeight = FontWeight.Bold)
                            Text("${et.start_sentiment} \u2192 ${et.end_sentiment}", style = MaterialTheme.typography.bodySmall)
                        }
                    }
                }

                // Graph
                item {
                    Text("Relationship Graph", fontWeight = FontWeight.Bold, modifier = Modifier.padding(top = 8.dp))
                }
                items(r.relationship_graph) { n ->
                    val riskColor = when (n.risk_profile) {
                        "critical" -> MaterialTheme.colorScheme.error
                        "high" -> MaterialTheme.colorScheme.tertiary
                        "moderate" -> MaterialTheme.colorScheme.secondary
                        else -> MaterialTheme.colorScheme.primary
                    }
                    Card(colors = CardDefaults.cardColors(containerColor = riskColor.copy(alpha = 0.1f))) {
                        Column(modifier = Modifier.padding(16.dp)) {
                            Text(n.name, fontWeight = FontWeight.Bold)
                            Text("${n.role} | ${n.risk_profile.uppercase()}", color = riskColor)
                            Text("Centrality: ${(n.centrality_score * 100).toInt()}%", style = MaterialTheme.typography.bodySmall)
                        }
                    }
                }
            }
        }
    }
}

// Data models for Android
@kotlinx.serialization.Serializable
data class OrbitScribeReport(
    val success: Boolean,
    val device_owner: String,
    val timestamp: String,
    val risk_level: String,
    val llm_used: Boolean,
    val mode: String,
    val overall_narrative: String,
    val attachment_analyses: List<AttachmentAnalysis> = emptyList(),
    val triangulation_events: List<TriangulationEvent> = emptyList(),
    val emotional_trajectories: List<EmotionalTrajectory> = emptyList(),
    val relationship_graph: List<RelationshipNode> = emptyList()
)

@kotlinx.serialization.Serializable
data class AttachmentAnalysis(
    val subject: String,
    val partner: String,
    val attachment_style: String,
    val evidence: List<String>,
    val confidence: Float
)

@kotlinx.serialization.Serializable
data class TriangulationEvent(
    val speaker: String,
    val target: String,
    val listener: String,
    val context: String,
    val manipulative_score: Float
)

@kotlinx.serialization.Serializable
data class EmotionalTrajectory(
    val thread_id: String,
    val start_sentiment: String,
    val end_sentiment: String,
    val trajectory: String
)

@kotlinx.serialization.Serializable
data class RelationshipNode(
    val name: String,
    val role: String,
    val centrality_score: Float,
    val risk_profile: String
)
