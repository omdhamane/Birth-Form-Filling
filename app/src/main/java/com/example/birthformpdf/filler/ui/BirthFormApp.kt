package com.example.birthformpdf.filler.ui

import android.content.ActivityNotFoundException
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.print.PrintAttributes
import android.print.PrintManager
import android.widget.Toast
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyListScope
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.ContentCopy
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.Edit
import androidx.compose.material.icons.filled.FileDownload
import androidx.compose.material.icons.filled.PictureAsPdf
import androidx.compose.material.icons.filled.Print
import androidx.compose.material.icons.filled.Share
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.ElevatedButton
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilterChip
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.core.content.FileProvider
import androidx.hilt.navigation.compose.hiltViewModel
import com.example.birthformpdf.filler.data.BirthRecord
import java.io.File

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun BirthFormApp(viewModel: BirthFormViewModel = hiltViewModel()) {
    val ui by viewModel.uiState.collectAsState()
    val records by viewModel.records.collectAsState()
    val text = labels(ui.language)
    val context = LocalContext.current
    val snackbar = remember { SnackbarHostState() }
    val savePdfLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.CreateDocument("application/pdf")
    ) { uri ->
        val pdf = ui.lastFile?.takeIf { it.extension.equals("pdf", ignoreCase = true) }
        if (uri != null && pdf != null) {
            context.copyFileToUri(pdf, uri)
            Toast.makeText(context, text.savePdf, Toast.LENGTH_SHORT).show()
        }
    }

    LaunchedEffect(ui.message) {
        ui.message?.let {
            snackbar.showSnackbar(it)
            viewModel.clearMessage()
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text(text.appTitle) },
                actions = {
                    FilterChip(
                        selected = ui.language == AppLanguage.EN,
                        onClick = { viewModel.setLanguage(AppLanguage.EN) },
                        label = { Text("EN") }
                    )
                    FilterChip(
                        selected = ui.language == AppLanguage.MR,
                        onClick = { viewModel.setLanguage(AppLanguage.MR) },
                        label = { Text("मराठी") },
                        modifier = Modifier.padding(horizontal = 8.dp)
                    )
                }
            )
        },
        snackbarHost = { SnackbarHost(snackbar) }
    ) { padding ->
        BoxWithConstraints(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(12.dp)
        ) {
            if (maxWidth < 840.dp) {
                Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                    FormPane(
                        modifier = Modifier.weight(1f),
                        labels = text,
                        record = ui.current,
                        errors = ui.errors,
                        lastFile = ui.lastFile,
                        onUpdate = viewModel::update,
                        onSave = viewModel::saveDraft,
                        onGenerate = viewModel::generatePdf,
                        onPreview = { ui.lastFile?.let { context.openFile(it) } },
                        onShare = { ui.lastFile?.let { context.shareFile(it) } },
                        onPrint = { ui.lastFile?.let { context.printPdf(it) } },
                        onSavePdf = { ui.lastFile?.let { savePdfLauncher.launch(it.name) } }
                    )
                    RecordsPane(
                        modifier = Modifier.weight(0.55f),
                        labels = text,
                        query = ui.query,
                        records = records,
                        onQuery = viewModel::search,
                        onNew = viewModel::newRecord,
                        onEdit = viewModel::edit,
                        onDelete = viewModel::delete,
                        onDuplicate = viewModel::duplicate,
                        onExport = { viewModel.export(records) }
                    )
                }
            } else {
                Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                    RecordsPane(
                        modifier = Modifier.weight(0.34f),
                        labels = text,
                        query = ui.query,
                        records = records,
                        onQuery = viewModel::search,
                        onNew = viewModel::newRecord,
                        onEdit = viewModel::edit,
                        onDelete = viewModel::delete,
                        onDuplicate = viewModel::duplicate,
                        onExport = { viewModel.export(records) }
                    )
                    FormPane(
                        modifier = Modifier.weight(0.66f),
                        labels = text,
                        record = ui.current,
                        errors = ui.errors,
                        lastFile = ui.lastFile,
                        onUpdate = viewModel::update,
                        onSave = viewModel::saveDraft,
                        onGenerate = viewModel::generatePdf,
                        onPreview = { ui.lastFile?.let { context.openFile(it) } },
                        onShare = { ui.lastFile?.let { context.shareFile(it) } },
                        onPrint = { ui.lastFile?.let { context.printPdf(it) } },
                        onSavePdf = { ui.lastFile?.let { savePdfLauncher.launch(it.name) } }
                    )
                }
            }
        }
    }
}

@Composable
private fun RecordsPane(
    modifier: Modifier,
    labels: Labels,
    query: String,
    records: List<BirthRecord>,
    onQuery: (String) -> Unit,
    onNew: () -> Unit,
    onEdit: (BirthRecord) -> Unit,
    onDelete: (BirthRecord) -> Unit,
    onDuplicate: (BirthRecord) -> Unit,
    onExport: () -> Unit
) {
    Column(modifier, verticalArrangement = Arrangement.spacedBy(10.dp)) {
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            OutlinedTextField(
                value = query,
                onValueChange = onQuery,
                label = { Text(labels.search) },
                modifier = Modifier.weight(1f),
                singleLine = true
            )
            IconButton(onClick = onNew) {
                Icon(Icons.Default.Add, contentDescription = labels.newRecord)
            }
            IconButton(onClick = onExport) {
                Icon(Icons.Default.FileDownload, contentDescription = labels.export)
            }
        }
        Text("${labels.records} (${records.size})", style = MaterialTheme.typography.titleMedium)
        LazyColumn(verticalArrangement = Arrangement.spacedBy(8.dp)) {
            items(records, key = { it.id }) { record ->
                Card(colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant)) {
                    Column(Modifier.padding(10.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                        Text(record.childName.ifBlank { labels.childName }, fontWeight = FontWeight.SemiBold)
                        Text(record.motherName)
                        Row(horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                            IconButton(onClick = { onEdit(record) }) { Icon(Icons.Default.Edit, labels.edit) }
                            IconButton(onClick = { onDuplicate(record) }) { Icon(Icons.Default.ContentCopy, labels.duplicate) }
                            IconButton(onClick = { onDelete(record) }) { Icon(Icons.Default.Delete, labels.delete) }
                        }
                    }
                }
            }
        }
    }
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun FormPane(
    modifier: Modifier,
    labels: Labels,
    record: BirthRecord,
    errors: Map<String, String>,
    lastFile: File?,
    onUpdate: (String, String) -> Unit,
    onSave: () -> Unit,
    onGenerate: () -> Unit,
    onPreview: () -> Unit,
    onShare: () -> Unit,
    onPrint: () -> Unit,
    onSavePdf: () -> Unit
) {
    val hasPdf = lastFile?.extension.equals("pdf", ignoreCase = true)
    LazyColumn(modifier, verticalArrangement = Arrangement.spacedBy(12.dp)) {
        item {
            FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                ElevatedButton(onClick = onGenerate) {
                    Icon(Icons.Default.PictureAsPdf, null)
                    Text(labels.generatePdf, Modifier.padding(start = 6.dp))
                }
                Button(onClick = onSave) { Text(labels.saveDraft) }
                IconButton(onClick = onPreview, enabled = hasPdf) { Icon(Icons.Default.PictureAsPdf, labels.preview) }
                IconButton(onClick = onSavePdf, enabled = hasPdf) { Icon(Icons.Default.FileDownload, labels.savePdf) }
                IconButton(onClick = onShare, enabled = hasPdf) { Icon(Icons.Default.Share, labels.share) }
                IconButton(onClick = onPrint, enabled = hasPdf) { Icon(Icons.Default.Print, labels.print) }
            }
        }
        section(labels.informantInfo) {
            field(labels.informantName, "informantName", record.informantName, errors, onUpdate)
            field(labels.relation, "relation", record.relation, errors, onUpdate)
            field(labels.mobileNumber, "mobileNumber", record.mobileNumber, errors, onUpdate)
        }
        section(labels.childInfo) {
            field(labels.childName, "childName", record.childName, errors, onUpdate)
            field(labels.gender, "gender", record.gender, errors, onUpdate)
            field(labels.dateOfBirth, "dateOfBirth", record.dateOfBirth, errors, onUpdate)
            field(labels.timeOfBirth, "timeOfBirth", record.timeOfBirth, errors, onUpdate)
            field(labels.placeOfBirth, "placeOfBirth", record.placeOfBirth, errors, onUpdate)
            field(labels.birthType, "birthType", record.birthType, errors, onUpdate)
        }
        section(labels.motherInfo) {
            field(labels.motherName, "motherName", record.motherName, errors, onUpdate)
            field(labels.aadhaarNumber, "motherAadhaar", record.motherAadhaar, errors, onUpdate)
            field(labels.age, "motherAge", record.motherAge, errors, onUpdate)
            field(labels.education, "motherEducation", record.motherEducation, errors, onUpdate)
            field(labels.occupation, "motherOccupation", record.motherOccupation, errors, onUpdate)
        }
        section(labels.fatherInfo) {
            field(labels.fatherName, "fatherName", record.fatherName, errors, onUpdate)
            field(labels.aadhaarNumber, "fatherAadhaar", record.fatherAadhaar, errors, onUpdate)
            field(labels.age, "fatherAge", record.fatherAge, errors, onUpdate)
            field(labels.education, "fatherEducation", record.fatherEducation, errors, onUpdate)
            field(labels.occupation, "fatherOccupation", record.fatherOccupation, errors, onUpdate)
        }
        section(labels.addressInfo) {
            field(labels.houseNumber, "houseNumber", record.houseNumber, errors, onUpdate)
            field(labels.street, "street", record.street, errors, onUpdate)
            field(labels.villageCity, "villageCity", record.villageCity, errors, onUpdate)
            field(labels.taluka, "taluka", record.taluka, errors, onUpdate)
            field(labels.district, "district", record.district, errors, onUpdate)
            field(labels.state, "state", record.state, errors, onUpdate)
            field(labels.pinCode, "pinCode", record.pinCode, errors, onUpdate)
        }
    }
}

private fun LazyListScope.section(title: String, content: @Composable () -> Unit) {
    item {
        Card {
            Column(Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text(title, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
                content()
            }
        }
    }
}

@Composable
private fun field(
    label: String,
    key: String,
    value: String,
    errors: Map<String, String>,
    onUpdate: (String, String) -> Unit
) {
    OutlinedTextField(
        value = value,
        onValueChange = { onUpdate(key, it) },
        label = { Text(label) },
        isError = errors.containsKey(key),
        supportingText = { errors[key]?.let { Text(it) } },
        modifier = Modifier.fillMaxWidth(),
        singleLine = true
    )
}

private fun Context.uriFor(file: File) =
    FileProvider.getUriForFile(this, "$packageName.fileprovider", file)

private fun Context.openFile(file: File) {
    val intent = Intent(Intent.ACTION_VIEW).apply {
        setDataAndType(uriFor(file), if (file.extension == "csv") "text/csv" else "application/pdf")
        addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
    }
    try {
        startActivity(intent)
    } catch (_: ActivityNotFoundException) {
        shareFile(file)
    }
}

private fun Context.shareFile(file: File) {
    val intent = Intent(Intent.ACTION_SEND).apply {
        type = if (file.extension == "csv") "text/csv" else "application/pdf"
        putExtra(Intent.EXTRA_STREAM, uriFor(file))
        addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
    }
    startActivity(Intent.createChooser(intent, file.name))
}

private fun Context.printPdf(file: File) {
    val adapter = PdfPrintAdapter(file)
    val printManager = getSystemService(Context.PRINT_SERVICE) as PrintManager
    printManager.print(
        file.nameWithoutExtension,
        adapter,
        PrintAttributes.Builder()
            .setMediaSize(PrintAttributes.MediaSize.ISO_A4)
            .setMinMargins(PrintAttributes.Margins.NO_MARGINS)
            .build()
    )
}

private fun Context.copyFileToUri(file: File, uri: Uri) {
    contentResolver.openOutputStream(uri)?.use { output ->
        file.inputStream().use { input -> input.copyTo(output) }
    }
}
