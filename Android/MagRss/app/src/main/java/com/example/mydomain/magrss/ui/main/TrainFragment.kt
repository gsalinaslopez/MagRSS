package com.example.mydomain.magrss.ui.main

import android.location.Location
import android.os.Bundle
import android.util.Log
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.ProgressBar
import android.widget.Switch
import android.widget.TextView
import android.widget.ToggleButton
import androidx.fragment.app.Fragment
import androidx.lifecycle.Observer
import androidx.lifecycle.ViewModelProviders
import androidx.transition.Visibility
import com.example.mydomain.magrss.R
import com.example.mydomain.magrss.viewmodel.TrainPageViewModel
import com.example.mydomain.magrss.viewmodel.TrainPageViewModelFactory
import com.google.android.gms.maps.*
import com.google.android.gms.maps.model.LatLng

class TrainFragment : Fragment() {

    private lateinit var trainPageViewModel: TrainPageViewModel

    private var toggleButtons  = mutableListOf<ToggleButton>()

    private lateinit var googleMap: GoogleMap

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        trainPageViewModel = ViewModelProviders.of(this,
            TrainPageViewModelFactory(context)
        )
            .get(TrainPageViewModel::class.java)
    }

    override fun onCreateView(
        inflater: LayoutInflater,
        container: ViewGroup?,
        savedInstanceState: Bundle?
    ): View? {
        val root = inflater.inflate(R.layout.fragment_train, container, false)

        (root.findViewById(R.id.train_switch) as Switch).setOnCheckedChangeListener { _, isChecked ->
            if (isChecked) {
                trainPageViewModel.observeAllLiveDataSources()

                (root.findViewById(R.id.progressBar) as ProgressBar).visibility = View.VISIBLE
                (root.findViewById(R.id.train_label_textView) as TextView).visibility = View.VISIBLE

            } else {
                trainPageViewModel.removeObserveAllLiveDataSources()
                (root.findViewById(R.id.progressBar) as ProgressBar).visibility = View.INVISIBLE
                (root.findViewById(R.id.train_label_textView) as TextView).visibility = View.INVISIBLE
            }
        }

        toggleButtons.add(0, (root.findViewById(R.id.onRoad_toggleButton) as ToggleButton))
        toggleButtons.add(1, (root.findViewById(R.id.onSidewalk_toggleButton) as ToggleButton))

        toggleButtons.forEachIndexed {index, toggleButton ->
            toggleButton.setOnClickListener { button ->
                val tButton = (button as ToggleButton)
                tButton.isChecked = true
                trainPageViewModel.setToggledButtonIndex(index)
            }
        }

        trainPageViewModel.toggledButtonIndex.observe(viewLifecycleOwner, Observer { data ->
            (root.findViewById(R.id.train_switch) as Switch).isEnabled = data.contains(true)
            data.forEachIndexed { index, checkedValue ->
                toggleButtons[index].isChecked = checkedValue
            }
        })

        val mapFragment = childFragmentManager
            .findFragmentById(R.id.mapFragment) as SupportMapFragment
        mapFragment.getMapAsync { map ->
            googleMap = map
            googleMap.isMyLocationEnabled = true
        }

        trainPageViewModel.positionSensorLiveData.observe(viewLifecycleOwner, Observer { data ->
            (root.findViewById(R.id.mag_x_textView) as TextView)
                .also { it.text = "X:" + data[1][0].toString()}
            (root.findViewById(R.id.mag_y_textView) as TextView)
                .also { it.text = "Y:" + data[1][1].toString()}
            (root.findViewById(R.id.mag_z_textView) as TextView)
                .also { it.text = "Z:" + data[1][2].toString()}
            (root.findViewById(R.id.heading_deg_textView) as TextView)
                .also {  it.text = "N:" + data[5][0].toString() + "°"}
        })

        trainPageViewModel.locationLiveData.observe(viewLifecycleOwner, Observer { data ->
            (root.findViewById(R.id.gps_lat_textView) as TextView)
                .also { it.text = "Lat:" + data["lat"].toString()}
            (root.findViewById(R.id.gps_lon_textView) as TextView)
                .also { it.text = "Lon:" + data["lon"].toString()}
            (root.findViewById(R.id.gps_acc_textView) as TextView)
                .also { it.text = "Acc:" + data["acc"].toString()}

            googleMap.animateCamera(
                CameraUpdateFactory.newLatLngZoom(LatLng(data["lat"]!!, data["lon"]!!), 18f)
            )
        })

        trainPageViewModel.telephonyLiveData.observe(viewLifecycleOwner, Observer { data ->
            (root.findViewById(R.id.lte_rsrp_textView) as TextView)
                .also { it.text = "RSRP:" + data[0]["rsrp"].toString()}
            (root.findViewById(R.id.lte_rsrq_textView) as TextView)
                .also { it.text = "RSRQ:" + data[0]["rsrq"].toString()}
            (root.findViewById(R.id.lte_rssnr_textView) as TextView)
                .also { it.text = "RSSNR:" + data[0]["rssnr"].toString()}
            (root.findViewById(R.id.lte_cqi_textView) as TextView)
                .also { it.text = "CQI:" + data[0]["cqi"].toString()}
            (root.findViewById(R.id.lte_dbm_textView) as TextView)
                .also { it.text = "dBm:" + data[0]["dbm"].toString()}
            (root.findViewById(R.id.lte_asu_textView) as TextView)
                .also { it.text = "ASU:" + data[0]["asuLevel"].toString()}
        })

        return root
    }

    companion object {
        @JvmStatic
        fun newInstance(): TrainFragment {
            return TrainFragment()
        }
    }
}