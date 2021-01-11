package com.example.mydomain.magrss.livedata

import android.content.Context
import android.location.Location
import android.os.Looper
import android.util.Log
import androidx.annotation.MainThread
import androidx.lifecycle.LiveData
import com.google.android.gms.common.api.ResolvableApiException
import com.google.android.gms.location.*
import com.google.android.gms.tasks.Task

class LocationLiveData(context: Context?): LiveData<Map<String, Double>>() {

    private val fusedLocationClient: FusedLocationProviderClient
    private val locationRequest: LocationRequest?
    private var locationSettingsResponseTask: Task<LocationSettingsResponse>
    private val locationCallback: LocationCallback
    private lateinit var location: Location

    init {
        fusedLocationClient = LocationServices.getFusedLocationProviderClient(context!!)
        locationRequest = LocationRequest.create()?.apply {
            interval = 100
            fastestInterval = 100
            priority = LocationRequest.PRIORITY_HIGH_ACCURACY
        }

        val builder = LocationSettingsRequest.Builder()
            .addLocationRequest(locationRequest!!)

        val client: SettingsClient = LocationServices.getSettingsClient(context)
        locationSettingsResponseTask = client.checkLocationSettings(builder.build())

        locationCallback = object : LocationCallback() {
            override fun onLocationResult(locationResult: LocationResult?) {
                super.onLocationResult(locationResult)
                locationResult ?: return
                location = locationResult.lastLocation

                val result = mapOf(
                    "lat" to location.latitude,
                    "lon" to location.longitude,
                    "acc" to location.accuracy.toDouble(),
                    "bear" to location.bearing.toDouble(),
                    "bearAcc" to location.bearingAccuracyDegrees.toDouble()
                )
                value = result
            }
        }
    }

    override fun onActive() {
        super.onActive()
        locationSettingsResponseTask.addOnSuccessListener { locationSettingsResponse ->
            Log.d("LOCATIONLIVEDATA", "All location settings are satisfied")
            fusedLocationClient.lastLocation.addOnSuccessListener {
                if (!::location.isInitialized and (it != null)) location = it
            }
            fusedLocationClient.requestLocationUpdates(
                locationRequest,
                locationCallback,
                Looper.getMainLooper()
            )
        }

        locationSettingsResponseTask.addOnFailureListener { exception ->
            if (exception is ResolvableApiException){
                Log.d("LOCATIONLIVEDATA", "All location settings are NOT satisfied")
            }
        }
    }

    override fun onInactive() {
        super.onInactive()
        fusedLocationClient.removeLocationUpdates(locationCallback)
    }

    companion object {
        private lateinit var sInstance: LocationLiveData

        @MainThread
        fun get(context: Context?) : LocationLiveData {
            sInstance = if (::sInstance.isInitialized) sInstance else LocationLiveData(context)
            return sInstance
        }
    }
}