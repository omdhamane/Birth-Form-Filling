package com.example.birthformpdf.filler.ui

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.birthformpdf.filler.data.BirthRecord
import com.example.birthformpdf.filler.data.BirthRecordRepository
import com.example.birthformpdf.filler.domain.CsvExporter
import com.example.birthformpdf.filler.domain.Validation
import com.example.birthformpdf.filler.pdf.PdfGenerator
import dagger.hilt.android.lifecycle.HiltViewModel
import java.io.File
import javax.inject.Inject
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.flatMapLatest
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class BirthFormUiState(
    val language: AppLanguage = AppLanguage.EN,
    val query: String = "",
    val current: BirthRecord = BirthRecord(),
    val errors: Map<String, String> = emptyMap(),
    val lastFile: File? = null,
    val message: String? = null
)

@OptIn(ExperimentalCoroutinesApi::class)
@HiltViewModel
class BirthFormViewModel @Inject constructor(
    private val repository: BirthRecordRepository,
    private val pdfGenerator: PdfGenerator,
    private val csvExporter: CsvExporter
) : ViewModel() {
    private val state = MutableStateFlow(BirthFormUiState())

    val uiState: StateFlow<BirthFormUiState> = state
    val records: StateFlow<List<BirthRecord>> = state
        .flatMapLatest { repository.observeRecords(it.query) }
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), emptyList())

    fun setLanguage(language: AppLanguage) = state.update { it.copy(language = language) }
    fun search(query: String) = state.update { it.copy(query = query) }
    fun newRecord() = state.update { it.copy(current = BirthRecord(), errors = emptyMap(), lastFile = null) }
    fun edit(record: BirthRecord) = state.update { it.copy(current = record, errors = emptyMap(), lastFile = null) }
    fun clearMessage() = state.update { it.copy(message = null) }

    fun update(field: String, value: String) {
        state.update {
            val r = it.current
            it.copy(current = when (field) {
                "childName" -> r.copy(childName = value)
                "gender" -> r.copy(gender = value)
                "dateOfBirth" -> r.copy(dateOfBirth = value)
                "timeOfBirth" -> r.copy(timeOfBirth = value)
                "placeOfBirth" -> r.copy(placeOfBirth = value)
                "birthType" -> r.copy(birthType = value)
                "motherName" -> r.copy(motherName = value)
                "motherAadhaar" -> r.copy(motherAadhaar = value)
                "motherAge" -> r.copy(motherAge = value)
                "motherEducation" -> r.copy(motherEducation = value)
                "motherOccupation" -> r.copy(motherOccupation = value)
                "fatherName" -> r.copy(fatherName = value)
                "fatherAadhaar" -> r.copy(fatherAadhaar = value)
                "fatherAge" -> r.copy(fatherAge = value)
                "fatherEducation" -> r.copy(fatherEducation = value)
                "fatherOccupation" -> r.copy(fatherOccupation = value)
                "houseNumber" -> r.copy(houseNumber = value)
                "street" -> r.copy(street = value)
                "villageCity" -> r.copy(villageCity = value)
                "taluka" -> r.copy(taluka = value)
                "district" -> r.copy(district = value)
                "state" -> r.copy(state = value)
                "pinCode" -> r.copy(pinCode = value)
                "informantName" -> r.copy(informantName = value)
                "relation" -> r.copy(relation = value)
                "mobileNumber" -> r.copy(mobileNumber = value)
                else -> r
            }, errors = it.errors - field)
        }
    }

    fun saveDraft() = viewModelScope.launch {
        val id = repository.save(state.value.current)
        state.update { it.copy(current = it.current.copy(id = id), message = labels(it.language).saved) }
    }

    fun generatePdf() = viewModelScope.launch {
        val errors = Validation.validate(state.value.current)
        if (errors.isNotEmpty()) {
            state.update { it.copy(errors = errors) }
            return@launch
        }
        val id = repository.save(state.value.current)
        val saved = state.value.current.copy(id = id)
        val file = pdfGenerator.generate(saved)
        state.update { it.copy(current = saved, lastFile = file, message = labels(it.language).pdfReady) }
    }

    fun delete(record: BirthRecord) = viewModelScope.launch {
        repository.delete(record)
        if (state.value.current.id == record.id) newRecord()
    }

    fun duplicate(record: BirthRecord) = viewModelScope.launch {
        repository.duplicate(record)
    }

    fun export(records: List<BirthRecord>) = viewModelScope.launch {
        val file = csvExporter.export(records)
        state.update { it.copy(lastFile = file, message = labels(it.language).exportReady) }
    }
}
