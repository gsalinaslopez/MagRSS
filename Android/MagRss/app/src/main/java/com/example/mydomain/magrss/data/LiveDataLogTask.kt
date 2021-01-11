package com.example.mydomain.magrss.data

import android.os.AsyncTask
import android.util.Log
import java.io.File
import java.io.FileWriter
import java.lang.Exception
import java.text.SimpleDateFormat
import java.util.*

class LiveDataLogTask(private val externalFilesDir: File?)
    : AsyncTask<List<Map<String, String>>, Int, Boolean>() {

    override fun doInBackground(vararg params: List<Map<String, String>>?): Boolean {
        var fileWriter: FileWriter? = null

        val logFileName =
            SimpleDateFormat("yyyy_MM_dd_HH_mm_ss").format(Date()) + "_train.csv"

        try {
            fileWriter = FileWriter(File(externalFilesDir, logFileName))

            fileWriter.append(params[0]!![0].keys.joinToString()).also { it.append('\n') }
            for (entry in params[0]!!.iterator()) {
                var size = 0

                entry!!.forEach { t, u ->

                    fileWriter.append(u)
                    if (++size != entry!!.size) {
                        fileWriter.append(',')
                    }
                }
                fileWriter.append('\n')
            }
        } catch (e: Exception) {
            Log.d("LOGTASK", "error: " + e.stackTrace)
        } finally {
            fileWriter!!.flush()
            fileWriter.close()
        }
        return true
    }
}