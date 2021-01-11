package com.example.mydomain.magrss.viewmodel

import android.content.Context
import android.util.Log
import androidx.lifecycle.*
import androidx.lifecycle.Observer
import com.example.mydomain.magrss.data.LiveDataLogTask
import com.example.mydomain.magrss.livedata.LocationLiveData
import com.example.mydomain.magrss.livedata.PositionSensorLiveData
import com.example.mydomain.magrss.livedata.TelephonyLiveData
import java.text.SimpleDateFormat
import java.util.*
import java.util.concurrent.Executors
import java.util.concurrent.ScheduledExecutorService
import java.util.concurrent.ScheduledFuture
import java.util.concurrent.TimeUnit
import java.util.concurrent.locks.Lock
import java.util.concurrent.locks.ReentrantLock

class TrainPageViewModel(context: Context?) : ViewModel() {

    var positionSensorData = mutableListOf<FloatArray>()
    val positionSensorDataLock = ReentrantLock()

    var telephonyData = mutableListOf<Map<String, Int>>()
    val telephonyDataLock = ReentrantLock()

    var locationData = mutableMapOf<String, Double>()
    val locationDataLock = ReentrantLock()

    lateinit var labelData: trainLabel

    var mergedLiveData = mutableListOf<Map<String, String>>()

    val liveDataMerger = MediatorLiveData<Map<String, String>>()
    val df = SimpleDateFormat("H")

    private var liveDataLoggerHandler: ScheduledFuture<*>? = null
    private val liveDataLoggerScheduler: ScheduledExecutorService =
        Executors.newSingleThreadScheduledExecutor()
    private val liveDataLogger = LiveDataLogger()

    var logFile = context!!.getExternalFilesDir(null)

    val positionSensorLiveData: PositionSensorLiveData by lazy {
        PositionSensorLiveData.get(context)
    }

    val telephonyLiveData: TelephonyLiveData by lazy {
        TelephonyLiveData.get(context)
    }

    val locationLiveData: LocationLiveData by lazy {
        LocationLiveData.get(context)
    }

    fun observeAllLiveDataSources() {
        mergedLiveData.clear()

        liveDataMerger.addSource(positionSensorLiveData) { data ->
            positionSensorDataLock.lock()
            try {
                positionSensorData.clear()
                positionSensorData = data
            } finally {
                positionSensorDataLock.unlock()
            }
        }

        liveDataMerger.addSource(telephonyLiveData) { data ->
            telephonyDataLock.lock()
            try {
                telephonyData.clear()
                telephonyData = data
            } finally {
                telephonyDataLock.unlock()
            }
        }

        liveDataMerger.addSource(locationLiveData) { data ->
            locationDataLock.lock()
            try {
                locationData.clear()
                locationData = data.toMutableMap()
            } finally {
                locationDataLock.unlock()
            }
        }

        liveDataMerger.observeForever({ ; })
        liveDataLoggerHandler = liveDataLoggerScheduler.scheduleAtFixedRate(
            liveDataLogger, 0, 200, TimeUnit.MILLISECONDS
        )

    }

    fun removeObserveAllLiveDataSources() {
        if (liveDataLoggerHandler != null) {
            liveDataMerger.removeObserver { ; }
            liveDataLoggerHandler!!.cancel(true)
            LiveDataLogTask(logFile).execute(mergedLiveData)
        }
    }

    inner class LiveDataLogger: Runnable {

        override fun run() {
            android.os.Process.setThreadPriority(android.os.Process.THREAD_PRIORITY_MORE_FAVORABLE)

            val entry = mutableMapOf<String, String>()

            locationDataLock.lock()
            try {
                entry.putAll(locationData.mapValues { it.value.toString() })
            } finally {
                locationDataLock.unlock()
            }

            positionSensorDataLock.lock()
            try {
                entry.put("magnetometer_x", positionSensorData[1][0].toString())
                entry.put("magnetometer_y", positionSensorData[1][1].toString())
                entry.put("magnetometer_z", positionSensorData[1][2].toString())
                entry.put("heading", positionSensorData[5][0].toString())
            } finally {
                positionSensorDataLock.unlock()
            }

            telephonyDataLock.lock()
            try {
                for (cellInfoEntry in telephonyData) {
                    val pid = cellInfoEntry["pid"]
                    val cellEntryMap = mutableMapOf<String, Int>()
                    cellEntryMap.putAll(cellInfoEntry)
                    cellEntryMap.remove("bandwidth")
                    cellEntryMap.remove("cid")
                    cellEntryMap.remove("pid")

                    val m = cellEntryMap.mapValues { pid.toString() + "_" + it.value.toString() }
                    val m2 = m.mapKeys { pid.toString() + "_" + it.key }
                    entry.putAll(m2)
                }
            } finally {
                telephonyDataLock.unlock()
            }

            entry["timestamp"] = df.format(Date())
            entry["label"] = labelData.name
            mergedLiveData.add(entry)

            Log.d(
                "LIVEDATALOGGER",
                "Adding entry " + entry.toString() + ", size:" + mergedLiveData.size.toString()
            )
        }
    }

    var toggledButtonIndex = MutableLiveData<BooleanArray>()

    fun setToggledButtonIndex(index: Int) {
        val result = booleanArrayOf(false, false)
        for (i in result.indices) {
            result[i] = false
            if (index == i) {
                result[i] = true
                labelData = trainLabel.values()[i]
            }
        }
        toggledButtonIndex.value = result
    }

    enum class trainLabel { ROAD, SIDEWALK }
}