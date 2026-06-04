package com.simplepod.unified.llm

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import java.net.URLEncoder

/**
 * ELI5: This is the utility room where we decide which power source to use.
 *      Try the local generator first (Ollama). If it trips offline,
 *      we auto-fallback to the grid (Pollinations.AI) so the lights stay on.
 */
class LLMClient(
    private val baseUrl: String = "http://10.0.2.2:8000", // Android emulator localhost
    private val timeoutMs: Int = 30000
) {

    suspend fun analyzeConversation(
        messages: List<Message>,
        context: String = "relationship"
    ): AnalysisResult = withContext(Dispatchers.IO) {
        val prompt = buildAnalysisPrompt(messages, context)
        val response = queryWithFallback(prompt)
        parseAnalysis(response)
    }

    suspend fun generateReply(
        thread: List<Message>,
        tone: String = "neutral",
        goal: String = "de-escalate"
    ): ReplyResult = withContext(Dispatchers.IO) {
        val prompt = buildReplyPrompt(thread, tone, goal)
        val response = queryWithFallback(prompt)
        ReplyResult(
            reply = response,
            tone = tone,
            confidence = 0.85f
        )
    }

    suspend fun getSwarmStatus(): SwarmStatus = withContext(Dispatchers.IO) {
        try {
            val url = URL("$baseUrl/unified/pipeline/status")
            val conn = url.openConnection() as HttpURLConnection
            conn.connectTimeout = timeoutMs
            conn.readTimeout = timeoutMs
            conn.requestMethod = "GET"

            val response = conn.inputStream.bufferedReader().use { it.readText() }
            val json = JSONObject(response)

            SwarmStatus(
                running = json.optBoolean("running", false),
                activeWorkers = json.optInt("active_workers", 0),
                queueDepth = json.optInt("queue_depth", 0),
                messagesProcessed = json.optLong("messages_processed", 0)
            )
        } catch (e: Exception) {
            SwarmStatus(running = false, activeWorkers = 0, queueDepth = 0, messagesProcessed = 0)
        }
    }

    private suspend fun queryWithFallback(prompt: String): String {
        // Try backend unified endpoint first
        try {
            val result = queryBackend(prompt)
            if (result.isNotBlank()) return result
        } catch (_: Exception) {}

        // Fallback to Pollinations.AI directly (free, no key)
        try {
            return queryPollinations(prompt)
        } catch (e: Exception) {
            return "Error: ${e.message}. Try checking your internet connection."
        }
    }

    private fun queryBackend(prompt: String): String {
        val url = URL("$baseUrl/unified/demo/llm-test")
        val conn = url.openConnection() as HttpURLConnection
        conn.connectTimeout = timeoutMs
        conn.readTimeout = timeoutMs
        conn.requestMethod = "POST"
        conn.setRequestProperty("Content-Type", "application/json")
        conn.doOutput = true

        val payload = JSONObject().put("prompt", prompt).toString()
        conn.outputStream.use { it.write(payload.toByteArray()) }

        val response = conn.inputStream.bufferedReader().use { it.readText() }
        return JSONObject(response).optString("response", "")
    }

    private fun queryPollinations(prompt: String): String {
        val encoded = URLEncoder.encode(prompt, "UTF-8")
        val url = URL("https://text.pollinations.ai/$encoded?model=openai&seed=42")
        val conn = url.openConnection() as HttpURLConnection
        conn.connectTimeout = timeoutMs
        conn.readTimeout = timeoutMs
        conn.setRequestProperty("Accept", "text/plain")

        return conn.inputStream.bufferedReader().use { it.readText() }
    }

    private fun buildAnalysisPrompt(messages: List<Message>, context: String): String {
        val sb = StringBuilder()
        sb.append("Analyze the following $context conversation for red flags, manipulation, abuse patterns, or concerning dynamics.\n\n")
        messages.forEach { msg ->
            sb.append("${msg.sender}: ${msg.body}\n")
        }
        sb.append("\nProvide:\n1. Overall sentiment (positive/neutral/negative)\n")
        sb.append("2. Red flags detected (list specific behaviors)\n")
        sb.append("3. Control score (0-10)\n")
        sb.append("4. Recommended action\n")
        return sb.toString()
    }

    private fun buildReplyPrompt(thread: List<Message>, tone: String, goal: String): String {
        val sb = StringBuilder()
        sb.append("You are a communication assistant. Generate a $tone reply that aims to $goal.\n\n")
        sb.append("Conversation thread:\n")
        thread.takeLast(10).forEach { msg ->
            sb.append("${msg.sender}: ${msg.body}\n")
        }
        sb.append("\nGenerate a single reply message:")
        return sb.toString()
    }

    private fun parseAnalysis(response: String): AnalysisResult {
        // Simple parsing — in production, use structured JSON from backend
        val redFlags = mutableListOf<String>()
        val lower = response.lowercase()

        if (lower.contains("control") || lower.contains("manipul")) redFlags.add("Controlling behavior")
        if (lower.contains("guilt") || lower.contains("blame")) redFlags.add("Guilt tripping")
        if (lower.contains("threat") || lower.contains("destroy")) redFlags.add("Threats detected")
        if (lower.contains("isolat") || lower.contains("alone")) redFlags.add("Isolation tactics")
        if (lower.contains("surveill") || lower.contains("track")) redFlags.add("Surveillance")

        val sentiment = when {
            lower.contains("positive") || lower.contains("healthy") -> "positive"
            lower.contains("negative") || lower.contains("abusive") -> "negative"
            else -> "neutral"
        }

        val controlScore = redFlags.size * 2f // Rough heuristic

        return AnalysisResult(
            sentiment = sentiment,
            redFlags = redFlags,
            controlScore = controlScore.coerceIn(0f, 10f),
            summary = response.take(500),
            recommendation = extractRecommendation(response)
        )
    }

    private fun extractRecommendation(response: String): String {
        val lines = response.lines()
        val recLine = lines.find { it.contains("recommend", ignoreCase = true) || it.contains("action", ignoreCase = true) }
        return recLine ?: "Consider discussing boundaries with a trusted friend or counselor."
    }

    data class Message(val sender: String, val body: String, val timestamp: Long = System.currentTimeMillis())
    data class AnalysisResult(
        val sentiment: String,
        val redFlags: List<String>,
        val controlScore: Float,
        val summary: String,
        val recommendation: String
    )
    data class ReplyResult(val reply: String, val tone: String, val confidence: Float)
    data class SwarmStatus(
        val running: Boolean,
        val activeWorkers: Int,
        val queueDepth: Int,
        val messagesProcessed: Long
    )

    suspend fun orbitscribeAnalyze(mode: String = "synthetic"): OrbitScribeReport? = withContext(Dispatchers.IO) {
        try {
            val url = URL("$baseUrl/unified/demo/orbitscribe/analyze?mode=$mode")
            val conn = url.openConnection() as HttpURLConnection
            conn.connectTimeout = timeoutMs * 6  // 3 min for analysis
            conn.readTimeout = timeoutMs * 6
            conn.requestMethod = "GET"

            val response = conn.inputStream.bufferedReader().use { it.readText() }
            val json = org.json.JSONObject(response)
            if (!json.optBoolean("success", false)) return@withContext null

            OrbitScribeReport(
                success = true,
                deviceOwner = json.optString("device_owner", ""),
                timestamp = json.optString("timestamp", ""),
                riskLevel = json.optString("risk_level", "unknown"),
                llmUsed = json.optBoolean("llm_used", false),
                mode = json.optString("mode", mode),
                overallNarrative = json.optString("overall_narrative", ""),
                attachmentAnalyses = parseAttachments(json.optJSONArray("attachment_analyses")),
                triangulationEvents = parseTriangulations(json.optJSONArray("triangulation_events")),
                emotionalTrajectories = parseTrajectories(json.optJSONArray("emotional_trajectories")),
                relationshipGraph = parseGraph(json.optJSONArray("relationship_graph"))
            )
        } catch (e: Exception) {
            null
        }
    }

    private fun parseAttachments(arr: org.json.JSONArray?): List<AttachmentAnalysis> {
        val list = mutableListOf<AttachmentAnalysis>()
        arr ?: return list
        for (i in 0 until arr.length()) {
            val obj = arr.getJSONObject(i)
            val evArr = obj.optJSONArray("evidence")
            val evidence = mutableListOf<String>()
            evArr?.let { for (j in 0 until it.length()) evidence.add(it.getString(j)) }
            list.add(AttachmentAnalysis(
                subject = obj.optString("subject", ""),
                partner = obj.optString("partner", ""),
                attachmentStyle = obj.optString("attachment_style", ""),
                evidence = evidence,
                confidence = obj.optDouble("confidence", 0.0).toFloat()
            ))
        }
        return list
    }

    private fun parseTriangulations(arr: org.json.JSONArray?): List<TriangulationEvent> {
        val list = mutableListOf<TriangulationEvent>()
        arr ?: return list
        for (i in 0 until arr.length()) {
            val obj = arr.getJSONObject(i)
            list.add(TriangulationEvent(
                speaker = obj.optString("speaker", ""),
                target = obj.optString("target", ""),
                listener = obj.optString("listener", ""),
                context = obj.optString("context", ""),
                manipulativeScore = obj.optDouble("manipulative_score", 0.0).toFloat()
            ))
        }
        return list
    }

    private fun parseTrajectories(arr: org.json.JSONArray?): List<EmotionalTrajectory> {
        val list = mutableListOf<EmotionalTrajectory>()
        arr ?: return list
        for (i in 0 until arr.length()) {
            val obj = arr.getJSONObject(i)
            list.add(EmotionalTrajectory(
                threadId = obj.optString("thread_id", ""),
                startSentiment = obj.optString("start_sentiment", ""),
                endSentiment = obj.optString("end_sentiment", ""),
                trajectory = obj.optString("trajectory", "")
            ))
        }
        return list
    }

    private fun parseGraph(arr: org.json.JSONArray?): List<RelationshipNode> {
        val list = mutableListOf<RelationshipNode>()
        arr ?: return list
        for (i in 0 until arr.length()) {
            val obj = arr.getJSONObject(i)
            list.add(RelationshipNode(
                name = obj.optString("name", ""),
                role = obj.optString("role", ""),
                centralityScore = obj.optDouble("centrality_score", 0.0).toFloat(),
                riskProfile = obj.optString("risk_profile", "low")
            ))
        }
        return list
    }

    data class AttachmentAnalysis(
        val subject: String,
        val partner: String,
        val attachmentStyle: String,
        val evidence: List<String>,
        val confidence: Float
    )
    data class TriangulationEvent(
        val speaker: String,
        val target: String,
        val listener: String,
        val context: String,
        val manipulativeScore: Float
    )
    data class EmotionalTrajectory(
        val threadId: String,
        val startSentiment: String,
        val endSentiment: String,
        val trajectory: String
    )
    data class RelationshipNode(
        val name: String,
        val role: String,
        val centralityScore: Float,
        val riskProfile: String
    )
    data class OrbitScribeReport(
        val success: Boolean,
        val deviceOwner: String,
        val timestamp: String,
        val riskLevel: String,
        val llmUsed: Boolean,
        val mode: String,
        val overallNarrative: String,
        val attachmentAnalyses: List<AttachmentAnalysis>,
        val triangulationEvents: List<TriangulationEvent>,
        val emotionalTrajectories: List<EmotionalTrajectory>,
        val relationshipGraph: List<RelationshipNode>
    )
}
