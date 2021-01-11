package com.example.mydomain.magrss

import android.os.Bundle
import android.util.Log
import com.google.android.material.tabs.TabLayout
import androidx.viewpager.widget.ViewPager
import androidx.appcompat.app.AppCompatActivity
import com.example.mydomain.magrss.ui.main.SectionsPagerAdapter
import com.google.android.gms.common.ConnectionResult
import com.google.android.gms.common.GoogleApiAvailability

class MainActivity : AppCompatActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)
        val sectionsPagerAdapter = SectionsPagerAdapter(this, supportFragmentManager)
        val viewPager: ViewPager = findViewById(R.id.view_pager)
        viewPager.adapter = sectionsPagerAdapter
        val tabs: TabLayout = findViewById(R.id.tabs)
        tabs.setupWithViewPager(viewPager)

        when (
            GoogleApiAvailability.getInstance().isGooglePlayServicesAvailable(
                applicationContext
            )
        ) {
            ConnectionResult.SUCCESS -> Log.d("GOOGLEPLAYSERICES", "SUCCESS")
            ConnectionResult.SERVICE_MISSING -> Log.d("GOOGLEPLAYSERICES", "SERVICE MISSING")
            ConnectionResult.SERVICE_UPDATING -> Log.d("GOOGLEPLAYSERICES", "SERVICE UPDATING")
            ConnectionResult.SERVICE_VERSION_UPDATE_REQUIRED -> Log.d("GOOGLEPLAYSERICES", "SERVICE VERSION UPDATE REQUIRED")
            ConnectionResult.SERVICE_DISABLED -> Log.d("GOOGLEPLAYSERICES", "SERVICE DISABLED")
            ConnectionResult.SERVICE_INVALID -> Log.d("GOOGLEPLAYSERICES", "SERVICE INVALID")
        }
    }
}