package com.example.birthformpdf.filler.di

import android.content.Context
import androidx.room.Room
import com.example.birthformpdf.filler.data.AppDatabase
import com.example.birthformpdf.filler.data.BirthRecordDao
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.android.qualifiers.ApplicationContext
import dagger.hilt.components.SingletonComponent
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
object AppModule {
    @Provides
    @Singleton
    fun provideDatabase(@ApplicationContext context: Context): AppDatabase =
        Room.databaseBuilder(context, AppDatabase::class.java, "birth_form_records.db").build()

    @Provides
    fun provideBirthRecordDao(database: AppDatabase): BirthRecordDao = database.birthRecordDao()
}
