package com.example.birthformpdf.filler

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import com.example.birthformpdf.filler.ui.BirthFormApp
import com.example.birthformpdf.filler.ui.theme.BirthFormTheme
import dagger.hilt.android.AndroidEntryPoint

@AndroidEntryPoint
class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            BirthFormTheme {
                BirthFormApp()
            }
        }
    }
}
