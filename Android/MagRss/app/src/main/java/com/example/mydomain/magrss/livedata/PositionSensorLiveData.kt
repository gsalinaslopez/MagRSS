package com.example.mydomain.magrss.livedata

import android.content.Context
import android.hardware.Sensor
import android.hardware.SensorEvent
import android.hardware.SensorEventListener
import android.hardware.SensorManager
import android.util.Log
import androidx.annotation.MainThread
import androidx.lifecycle.LiveData
import com.kircherelectronics.fsensor.filter.averaging.LowPassFilter
import com.kircherelectronics.fsensor.filter.gyroscope.OrientationGyroscope
import com.kircherelectronics.fsensor.filter.gyroscope.fusion.OrientationFused
import com.kircherelectronics.fsensor.filter.gyroscope.fusion.complimentary.OrientationFusedComplimentary
import com.kircherelectronics.fsensor.filter.gyroscope.fusion.kalman.OrientationFusedKalman
import com.kircherelectronics.fsensor.linearacceleration.LinearAcceleration
import com.kircherelectronics.fsensor.linearacceleration.LinearAccelerationFusion
import com.kircherelectronics.fsensor.util.rotation.RotationUtil
import org.apache.commons.math3.complex.Quaternion
import java.nio.channels.FileLock
import kotlin.math.sqrt

class PositionSensorLiveData(context: Context?) : LiveData<MutableList<FloatArray>>() {

    private val sensorManager: SensorManager
    private val positionSensorEventListener: PositionSensorEventListener

    init {
        sensorManager = context!!.getSystemService(Context.SENSOR_SERVICE) as SensorManager
        positionSensorEventListener = PositionSensorEventListener()
        initFilterSensorFusion()
    }

    override fun onActive() {
        super.onActive()
        registerPositionSensorEventListener()
    }

    override fun onInactive() {
        super.onInactive()
        sensorManager.unregisterListener(positionSensorEventListener)
    }

    companion object {
        private lateinit var sInstance: PositionSensorLiveData

        @MainThread
        fun get(context: Context?) : PositionSensorLiveData {
            sInstance = if (::sInstance.isInitialized) sInstance else PositionSensorLiveData(context)
            return sInstance
        }
    }

    // FSensor filters and sensor fusion
    private lateinit var orientationFusionComplimentary: OrientationFusedComplimentary
    private lateinit var orientationFusionKalman: OrientationFusedKalman
    private lateinit var orientationGyroscope: OrientationGyroscope
    private enum class orientationFusionMode { RAW, COMPLIMENTARY, KALMAN }
    private val mode = orientationFusionMode.COMPLIMENTARY

    private fun initFilterSensorFusion() {
        orientationFusionComplimentary = OrientationFusedComplimentary()
        orientationFusionKalman = OrientationFusedKalman()
        orientationGyroscope = OrientationGyroscope()
    }

    private fun registerPositionSensorEventListener() {
        sensorManager.getDefaultSensor(Sensor.TYPE_ACCELEROMETER)?.also { accelerometer ->
            sensorManager.registerListener(
                positionSensorEventListener,
                accelerometer,
                SensorManager.SENSOR_DELAY_FASTEST,
                SensorManager.SENSOR_DELAY_UI)
        }

        sensorManager.getDefaultSensor(Sensor.TYPE_MAGNETIC_FIELD)?.also { magneticField ->
            sensorManager.registerListener(
                positionSensorEventListener,
                magneticField,
                SensorManager.SENSOR_DELAY_FASTEST,
                SensorManager.SENSOR_DELAY_UI
            )
        }

        sensorManager.getDefaultSensor(Sensor.TYPE_GYROSCOPE)?.also { gyroscope ->
            sensorManager.registerListener(
                positionSensorEventListener,
                gyroscope,
                SensorManager.SENSOR_DELAY_FASTEST,
                SensorManager.SENSOR_DELAY_UI
            )
        }
    }

    // Raw sensor values
    private lateinit var accelerometerReading: FloatArray
    private lateinit var magnetometerReading: FloatArray
    private var gyroscopeReading = FloatArray(3)

    // Processed raw sensor values
    private var fusedOrientation = FloatArray(3)
    private val rotationMatrix = FloatArray(9)
    private val orientationAngles = FloatArray(3)

    private val normalizedAccelerometerReading = FloatArray(3)
    private val normalizedMagnetometerReading = FloatArray(3)
    private val normalizedRotationMatrix = FloatArray(9)
    private val normalizedOrientationAngles = FloatArray(3)
    private val heading = FloatArray(1)

    val alpha = 0.97f

    /***
     * SensorEventListener class that implements callbacks for the multiple sensors
     */
    inner class PositionSensorEventListener : SensorEventListener {
        override fun onAccuracyChanged(sensor: Sensor?, accuracy: Int) { }

        /***
         * Process various raw sensor readings
         */
        override fun onSensorChanged(event: SensorEvent) {
            if (event.sensor.type == Sensor.TYPE_ACCELEROMETER) {
                processAccelerometer(event.values)
            } else if (event.sensor.type == Sensor.TYPE_MAGNETIC_FIELD) {
                processMagnetometer(event.values)
            } else if (event.sensor.type == Sensor.TYPE_GYROSCOPE) {
                processGyroscope(event.values, event.timestamp)
            }

            if (::accelerometerReading.isInitialized and ::magnetometerReading.isInitialized) {
                updateOrientationAngles()
                updateLiveData()
            }
        }
    }

    fun processAccelerometer(values: FloatArray) {
        if (!::accelerometerReading.isInitialized) {
            accelerometerReading = FloatArray(3)
        }
        System.arraycopy(values, 0, accelerometerReading, 0, accelerometerReading.size)

        normalizedAccelerometerReading[0] =
            alpha * normalizedAccelerometerReading[0] + (1 - alpha) * values[0]
        normalizedAccelerometerReading[1] =
            alpha * normalizedAccelerometerReading[1] + (1 - alpha) * values[1]
        normalizedAccelerometerReading[2] =
            alpha * normalizedAccelerometerReading[2] + (1 - alpha) * values[2]
    }

    fun processMagnetometer(values: FloatArray) {
        if (!::magnetometerReading.isInitialized) {
            magnetometerReading = FloatArray(3)
        }
        System.arraycopy(values, 0, magnetometerReading, 0, magnetometerReading.size)

        normalizedMagnetometerReading[0] =
            alpha * normalizedMagnetometerReading[0] + (1 - alpha) * values[0]
        normalizedMagnetometerReading[1] =
            alpha * normalizedMagnetometerReading[1] + (1 - alpha) * values[1]
        normalizedMagnetometerReading[2] =
            alpha * normalizedMagnetometerReading[2] + (1 - alpha) * values[2]
    }

    fun processGyroscope(values: FloatArray, timestamp: Long) {
        System.arraycopy(values, 0, gyroscopeReading, 0, gyroscopeReading.size)

        when (mode) {
            orientationFusionMode.RAW -> {
                if (!orientationGyroscope.isBaseOrientationSet) {
                    orientationGyroscope.setBaseOrientation(Quaternion.IDENTITY)
                } else {
                    fusedOrientation = orientationGyroscope.calculateOrientation(
                        gyroscopeReading, timestamp
                    )
                }
            }
            orientationFusionMode.COMPLIMENTARY -> {
                if (
                    !orientationFusionComplimentary.isBaseOrientationSet and
                    ::accelerometerReading.isInitialized and
                    ::magnetometerReading.isInitialized
                ) {
                    orientationFusionComplimentary.setBaseOrientation(
                        RotationUtil.getOrientationVectorFromAccelerationMagnetic(
                            accelerometerReading, magnetometerReading
                        )
                    )
                } else {
                    fusedOrientation = orientationFusionComplimentary.calculateFusedOrientation(
                        gyroscopeReading, timestamp, accelerometerReading, magnetometerReading
                    )
                }
            }
            orientationFusionMode.KALMAN -> {
                if (
                    !orientationFusionKalman.isBaseOrientationSet and
                    ::accelerometerReading.isInitialized and
                    ::magnetometerReading.isInitialized
                ) {
                    orientationFusionKalman.setBaseOrientation(
                        RotationUtil.getOrientationVectorFromAccelerationMagnetic(
                            accelerometerReading, magnetometerReading
                        )
                    )
                } else {
                    fusedOrientation = orientationFusionKalman.calculateFusedOrientation(
                        gyroscopeReading, timestamp, accelerometerReading, magnetometerReading)
                }
            }
        }
    }

    fun updateOrientationAngles() {
        // Using Raw inputs
        SensorManager.getRotationMatrix(
            rotationMatrix,
            null,
            accelerometerReading,
            magnetometerReading
        )
        SensorManager.getOrientation(rotationMatrix, orientationAngles)
        for (i in orientationAngles.indices) {
            orientationAngles[i] = Math.toDegrees(orientationAngles[i].toDouble()).toFloat()
        }
        // Using processed input
        SensorManager.getRotationMatrix(
            normalizedRotationMatrix,
            null,
            normalizedAccelerometerReading,
            normalizedMagnetometerReading
        )
        SensorManager.getOrientation(normalizedRotationMatrix, normalizedOrientationAngles)

        heading[0] = (Math.toDegrees(normalizedOrientationAngles[0].toDouble())).also {
            (it + 360) % 360
        }.toFloat()
    }

    fun updateLiveData() {
        val result = mutableListOf<FloatArray>()
        result.add(accelerometerReading)
        result.add(magnetometerReading)
        result.add(gyroscopeReading)
        result.add(fusedOrientation)
        result.add(rotationMatrix)
        result.add(orientationAngles)
        result.add(heading)
        value = result
    }
}