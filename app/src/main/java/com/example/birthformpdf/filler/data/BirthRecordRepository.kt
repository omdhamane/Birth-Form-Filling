package com.example.birthformpdf.filler.data

import kotlinx.coroutines.flow.Flow
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class BirthRecordRepository @Inject constructor(
    private val dao: BirthRecordDao
) {
    fun observeRecords(query: String): Flow<List<BirthRecord>> = dao.observeRecords(query)
    suspend fun save(record: BirthRecord): Long =
        if (record.id == 0L) dao.insert(record.copy(updatedAt = System.currentTimeMillis()))
        else {
            dao.update(record.copy(updatedAt = System.currentTimeMillis()))
            record.id
        }

    suspend fun get(id: Long): BirthRecord? = dao.getById(id)
    suspend fun delete(record: BirthRecord) = dao.delete(record)
    suspend fun duplicate(record: BirthRecord): Long = dao.insert(
        record.copy(id = 0, childName = "${record.childName} Copy", createdAt = System.currentTimeMillis(), updatedAt = System.currentTimeMillis())
    )
}
