package com.example.mydomain.magrss.livedata

import android.content.Context
import android.telephony.*
import androidx.annotation.MainThread
import androidx.lifecycle.LiveData

class TelephonyLiveData(context: Context?): LiveData<MutableList<Map<String, Int>>>() {
    private val telephonyManager: TelephonyManager
    private val phoneStateListener: phoneCellInfoStateListener

    init {
        telephonyManager = context!!.getSystemService(Context.TELEPHONY_SERVICE) as TelephonyManager
        phoneStateListener = phoneCellInfoStateListener()
    }

    override fun onActive() {
        super.onActive()
        telephonyManager.listen(
            phoneStateListener,
            PhoneStateListener.LISTEN_CELL_INFO or PhoneStateListener.LISTEN_SIGNAL_STRENGTHS
        )
    }

    override fun onInactive() {
        super.onInactive()
        telephonyManager.listen(phoneStateListener, PhoneStateListener.LISTEN_NONE)
    }

    companion object {
        private lateinit var sInstance: TelephonyLiveData

        @MainThread
        fun get(context: Context?) : TelephonyLiveData {
            sInstance = if (::sInstance.isInitialized) sInstance else TelephonyLiveData(context)
            return sInstance
        }
    }

    inner class phoneCellInfoStateListener: PhoneStateListener() {
        override fun onCellInfoChanged(cellInfo: MutableList<CellInfo>?) {
            super.onCellInfoChanged(cellInfo)
            onNewCellInfo(telephonyManager.allCellInfo)
        }

        override fun onSignalStrengthsChanged(signalStrength: SignalStrength?) {
            super.onSignalStrengthsChanged(signalStrength)
            onNewCellInfo(telephonyManager.allCellInfo)
        }
    }

    fun onNewCellInfo(cellInfoList: MutableList<CellInfo>?) {
        if (cellInfoList == null) return

        val result = mutableListOf<Map<String, Int>>()

        for (cellInfo in cellInfoList) {
            if (cellInfo is CellInfoLte) {
                result.add(
                    processCellIdentity(cellInfo.cellIdentity) +
                    processCellSignalStrength(cellInfo.cellSignalStrength)
                )
            }
        }

        value = result
    }

    fun processCellIdentity(cellIdentityLte: CellIdentityLte): Map<String, Int> {
        val m = mutableMapOf(
            "bandwidth" to cellIdentityLte.bandwidth,
            "cid" to cellIdentityLte.ci,
            "pid" to cellIdentityLte.pci
        )
        return m
    }

    fun processCellSignalStrength(cellSignalStrengthLte: CellSignalStrengthLte): Map<String, Int> {
        val m = mutableMapOf(
            "asuLevel" to cellSignalStrengthLte.asuLevel,
            "cqi" to cellSignalStrengthLte.cqi,
            "dbm" to cellSignalStrengthLte.dbm,
            "level" to cellSignalStrengthLte.level,
            "rsrp" to cellSignalStrengthLte.rsrp,
            "rsrq" to cellSignalStrengthLte.rsrq,
            "rssnr" to cellSignalStrengthLte.rssnr
        )
        return m
    }
}