package com.example.birthformpdf.filler.domain

import com.example.birthformpdf.filler.data.BirthRecord

object Validation {
    private val dateRegex = Regex("""\d{2}/\d{2}/\d{4}""")
    private val timeRegex = Regex("""\d{2}:\d{2}""")
    private val aadhaarRegex = Regex("""\d{12}""")
    private val mobileRegex = Regex("""[6-9]\d{9}""")

    fun validate(record: BirthRecord): Map<String, String> = buildMap {
        required("childName", record.childName)
        required("dateOfBirth", record.dateOfBirth)
        required("placeOfBirth", record.placeOfBirth)
        required("motherName", record.motherName)
        required("fatherName", record.fatherName)
        required("informantName", record.informantName)
        required("mobileNumber", record.mobileNumber)
        if (record.dateOfBirth.isNotBlank() && !dateRegex.matches(record.dateOfBirth)) put("dateOfBirth", "Use DD/MM/YYYY")
        if (record.timeOfBirth.isNotBlank() && !timeRegex.matches(record.timeOfBirth)) put("timeOfBirth", "Use HH:MM")
        if (record.motherAadhaar.isNotBlank() && !aadhaarRegex.matches(record.motherAadhaar)) put("motherAadhaar", "Enter 12 digits")
        if (record.fatherAadhaar.isNotBlank() && !aadhaarRegex.matches(record.fatherAadhaar)) put("fatherAadhaar", "Enter 12 digits")
        if (record.mobileNumber.isNotBlank() && !mobileRegex.matches(record.mobileNumber)) put("mobileNumber", "Enter 10 digit Indian mobile")
    }

    private fun MutableMap<String, String>.required(field: String, value: String) {
        if (value.isBlank()) put(field, "Required")
    }
}
