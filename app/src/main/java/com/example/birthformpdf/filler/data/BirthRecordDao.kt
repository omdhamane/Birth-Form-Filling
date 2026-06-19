package com.example.birthformpdf.filler.data

import androidx.room.Dao
import androidx.room.Delete
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import androidx.room.Update
import kotlinx.coroutines.flow.Flow

@Dao
interface BirthRecordDao {
    @Query(
        """
        SELECT * FROM birth_records
        WHERE :query = ''
           OR childName LIKE '%' || :query || '%'
           OR motherName LIKE '%' || :query || '%'
           OR fatherName LIKE '%' || :query || '%'
           OR informantName LIKE '%' || :query || '%'
           OR mobileNumber LIKE '%' || :query || '%'
        ORDER BY updatedAt DESC
        """
    )
    fun observeRecords(query: String): Flow<List<BirthRecord>>

    @Query("SELECT * FROM birth_records WHERE id = :id")
    suspend fun getById(id: Long): BirthRecord?

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insert(record: BirthRecord): Long

    @Update
    suspend fun update(record: BirthRecord)

    @Delete
    suspend fun delete(record: BirthRecord)
}
