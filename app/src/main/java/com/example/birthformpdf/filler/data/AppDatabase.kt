package com.example.birthformpdf.filler.data

import androidx.room.Database
import androidx.room.RoomDatabase

@Database(entities = [BirthRecord::class], version = 1, exportSchema = true)
abstract class AppDatabase : RoomDatabase() {
    abstract fun birthRecordDao(): BirthRecordDao
}
