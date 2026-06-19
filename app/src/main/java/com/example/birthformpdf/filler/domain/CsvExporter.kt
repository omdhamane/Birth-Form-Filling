package com.example.birthformpdf.filler.domain

import android.content.Context
import com.example.birthformpdf.filler.data.BirthRecord
import dagger.hilt.android.qualifiers.ApplicationContext
import java.io.File
import javax.inject.Inject

class CsvExporter @Inject constructor(
    @ApplicationContext private val context: Context
) {
    fun export(records: List<BirthRecord>): File {
        val file = File(context.filesDir, "birth_records_export.csv")
        file.writeText(buildCsv(records), Charsets.UTF_8)
        return file
    }

    private fun buildCsv(records: List<BirthRecord>): String {
        val header = listOf(
            "Child Name", "Gender", "Date of Birth", "Time of Birth", "Place of Birth", "Birth Type",
            "Mother Name", "Mother Aadhaar", "Mother Age", "Mother Education", "Mother Occupation",
            "Father Name", "Father Aadhaar", "Father Age", "Father Education", "Father Occupation",
            "Address", "Informant Name", "Relation", "Mobile Number"
        )
        val rows = records.map { r ->
            listOf(
                r.childName, r.gender, r.dateOfBirth, r.timeOfBirth, r.placeOfBirth, r.birthType,
                r.motherName, r.motherAadhaar, r.motherAge, r.motherEducation, r.motherOccupation,
                r.fatherName, r.fatherAadhaar, r.fatherAge, r.fatherEducation, r.fatherOccupation,
                r.addressLine, r.informantName, r.relation, r.mobileNumber
            )
        }
        return (listOf(header) + rows).joinToString("\n") { row -> row.joinToString(",") { it.csv() } }
    }

    private fun String.csv(): String = "\"" + replace("\"", "\"\"") + "\""
}
