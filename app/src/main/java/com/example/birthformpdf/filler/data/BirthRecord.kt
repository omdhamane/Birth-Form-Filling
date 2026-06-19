package com.example.birthformpdf.filler.data

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "birth_records")
data class BirthRecord(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val childName: String = "",
    val gender: String = "",
    val dateOfBirth: String = "",
    val timeOfBirth: String = "",
    val placeOfBirth: String = "",
    val birthType: String = "",
    val motherName: String = "",
    val motherAadhaar: String = "",
    val motherAge: String = "",
    val motherEducation: String = "",
    val motherOccupation: String = "",
    val fatherName: String = "",
    val fatherAadhaar: String = "",
    val fatherAge: String = "",
    val fatherEducation: String = "",
    val fatherOccupation: String = "",
    val houseNumber: String = "",
    val street: String = "",
    val villageCity: String = "",
    val taluka: String = "",
    val district: String = "",
    val state: String = "",
    val pinCode: String = "",
    val informantName: String = "",
    val relation: String = "",
    val mobileNumber: String = "",
    val createdAt: Long = System.currentTimeMillis(),
    val updatedAt: Long = System.currentTimeMillis()
) {
    val addressLine: String
        get() = listOf(houseNumber, street, villageCity, taluka, district, state, pinCode)
            .filter { it.isNotBlank() }
            .joinToString(", ")
}
