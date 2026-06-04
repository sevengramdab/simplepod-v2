package com.simplepod.unified.sms

import android.content.ContentResolver
import android.content.Context
import android.net.Uri
import android.provider.Telephony
import com.simplepod.unified.llm.LLMClient

/**
 * ELI5: This is the phone company's message archive room.
 *      We can read the logbooks (SMS threads), analyze them,
 *      and even inject new messages back into the system (MMS/SMS thread injection).
 */
class SMSManager(private val context: Context) {

    private val llmClient = LLMClient()

    data class ThreadSummary(
        val threadId: Long,
        val address: String,
        val snippet: String,
        val messageCount: Int,
        val lastDate: Long
    )

    data class Message(
        val id: Long,
        val threadId: Long,
        val address: String,
        val body: String,
        val date: Long,
        val type: Int // 1 = inbox, 2 = sent
    )

    fun getAllThreads(): List<ThreadSummary> {
        val threads = mutableListOf<ThreadSummary>()
        val cursor = context.contentResolver.query(
            Telephony.Sms.Conversations.CONTENT_URI,
            arrayOf(
                Telephony.Sms.Conversations.THREAD_ID,
                Telephony.Sms.Conversations.SNIPPET,
                Telephony.Sms.Conversations.MESSAGE_COUNT
            ),
            null, null,
            Telephony.Sms.Conversations.DEFAULT_SORT_ORDER
        )

        cursor?.use {
            while (it.moveToNext()) {
                val threadId = it.getLong(0)
                val snippet = it.getString(1) ?: ""
                val count = it.getInt(2)

                // Get the address (contact phone number) from the first message in thread
                val address = getThreadAddress(threadId)
                val lastDate = getThreadLastDate(threadId)

                threads.add(ThreadSummary(threadId, address, snippet, count, lastDate))
            }
        }
        return threads
    }

    fun getThreadMessages(threadId: Long): List<Message> {
        val messages = mutableListOf<Message>()
        val cursor = context.contentResolver.query(
            Telephony.Sms.CONTENT_URI,
            arrayOf(
                Telephony.Sms._ID,
                Telephony.Sms.THREAD_ID,
                Telephony.Sms.ADDRESS,
                Telephony.Sms.BODY,
                Telephony.Sms.DATE,
                Telephony.Sms.TYPE
            ),
            "${Telephony.Sms.THREAD_ID} = ?",
            arrayOf(threadId.toString()),
            "${Telephony.Sms.DATE} ASC"
        )

        cursor?.use {
            while (it.moveToNext()) {
                messages.add(Message(
                    id = it.getLong(0),
                    threadId = it.getLong(1),
                    address = it.getString(2) ?: "Unknown",
                    body = it.getString(3) ?: "",
                    date = it.getLong(4),
                    type = it.getInt(5)
                ))
            }
        }
        return messages
    }

    suspend fun analyzeThread(threadId: Long): LLMClient.AnalysisResult {
        val messages = getThreadMessages(threadId).map { msg ->
            LLMClient.Message(
                sender = if (msg.type == 1) msg.address else "Me",
                body = msg.body,
                timestamp = msg.date
            )
        }
        return llmClient.analyzeConversation(messages)
    }

    suspend fun generateReplyForThread(threadId: Long, tone: String, goal: String): LLMClient.ReplyResult {
        val messages = getThreadMessages(threadId).map { msg ->
            LLMClient.Message(
                sender = if (msg.type == 1) msg.address else "Me",
                body = msg.body,
                timestamp = msg.date
            )
        }
        return llmClient.generateReply(messages, tone, goal)
    }

    private fun getThreadAddress(threadId: Long): String {
        val cursor = context.contentResolver.query(
            Telephony.Sms.CONTENT_URI,
            arrayOf(Telephony.Sms.ADDRESS),
            "${Telephony.Sms.THREAD_ID} = ?",
            arrayOf(threadId.toString()),
            "${Telephony.Sms.DATE} DESC"
        )
        return cursor?.use {
            if (it.moveToFirst()) it.getString(0) ?: "Unknown" else "Unknown"
        } ?: "Unknown"
    }

    private fun getThreadLastDate(threadId: Long): Long {
        val cursor = context.contentResolver.query(
            Telephony.Sms.CONTENT_URI,
            arrayOf(Telephony.Sms.DATE),
            "${Telephony.Sms.THREAD_ID} = ?",
            arrayOf(threadId.toString()),
            "${Telephony.Sms.DATE} DESC"
        )
        return cursor?.use {
            if (it.moveToFirst()) it.getLong(0) else 0L
        } ?: 0L
    }
}
