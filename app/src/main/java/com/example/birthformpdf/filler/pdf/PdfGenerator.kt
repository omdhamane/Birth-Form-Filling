package com.example.birthformpdf.filler.pdf

import android.content.Context
import com.example.birthformpdf.filler.data.BirthRecord
import com.tom_roush.pdfbox.pdmodel.PDDocument
import com.tom_roush.pdfbox.pdmodel.PDPageContentStream
import com.tom_roush.pdfbox.pdmodel.font.PDType0Font
import dagger.hilt.android.qualifiers.ApplicationContext
import java.io.File
import javax.inject.Inject

class PdfGenerator @Inject constructor(
    @ApplicationContext private val context: Context
) {
    fun generate(record: BirthRecord): File {
        val output = File(context.filesDir, "birth_form_${record.id.takeIf { it != 0L } ?: System.currentTimeMillis()}.pdf")
        context.assets.open(TEMPLATE_ASSET).use { template ->
            PDDocument.load(template).use { document ->
                document.documentCatalog.acroForm?.flatten()
                val font = context.assets.open(FONT_ASSET).use { PDType0Font.load(document, it, true) }
                val page = document.getPage(PdfCoordinates.PAGE_ONE)
                PDPageContentStream(
                    document,
                    page,
                    PDPageContentStream.AppendMode.APPEND,
                    true,
                    true
                ).use { stream ->
                    stream.setNonStrokingColor(0, 0, 0)
                    writeAll(stream, font, record)
                }
                document.save(output)
            }
        }
        return output
    }

    private fun writeAll(stream: PDPageContentStream, font: PDType0Font, record: BirthRecord) {
        val address = record.addressLine
        val applicantAge = record.informantAge()
        val addressLines = address.toLines(maxChars = 72, maxLines = 2)
        text(stream, font, record.informantName.uppercase(), PdfCoordinates.APPLICANT_NAME_X, PdfCoordinates.APPLICANT_NAME_Y, 7.6f, 36, 155f)
        text(stream, font, addressLines.getOrNull(0).orEmpty(), PdfCoordinates.APPLICANT_ADDRESS_LINE_1_X, PdfCoordinates.APPLICANT_ADDRESS_LINE_1_Y, 7.6f, 64, 230f)
        text(stream, font, addressLines.getOrNull(1).orEmpty(), PdfCoordinates.APPLICANT_ADDRESS_LINE_2_X, PdfCoordinates.APPLICANT_ADDRESS_LINE_2_Y, 7.6f, 76, 255f)
        text(stream, font, today(), PdfCoordinates.FORM_DATE_X, PdfCoordinates.FORM_DATE_Y, 8.2f, 20, 95f)

        text(stream, font, record.informantName.uppercase(), PdfCoordinates.DECLARATION_APPLICANT_X, PdfCoordinates.DECLARATION_APPLICANT_Y, 7.6f, 32, 180f)
        text(stream, font, applicantAge, PdfCoordinates.APPLICANT_AGE_X, PdfCoordinates.APPLICANT_AGE_Y, 7.6f, 4, 28f)
        text(stream, font, record.relation.uppercase(), PdfCoordinates.RELATION_X, PdfCoordinates.RELATION_Y, 7.6f, 18, 110f)
        text(stream, font, record.dateOfBirth, PdfCoordinates.CHILD_DOB_DECLARATION_X, PdfCoordinates.CHILD_DOB_DECLARATION_Y, 7.6f, 16, 60f)
        text(stream, font, record.placeOfBirth.uppercase(), PdfCoordinates.PLACE_OF_BIRTH_X, PdfCoordinates.PLACE_OF_BIRTH_Y, 7.6f, 38, 260f)

        text(stream, font, record.childName, PdfCoordinates.CHILD_NAME_MR_X, PdfCoordinates.CHILD_NAME_MR_Y, 8.4f, 46, 215f)
        text(stream, font, record.childName, PdfCoordinates.CHILD_NAME_EN_X, PdfCoordinates.CHILD_NAME_EN_Y, 8.4f, 46, 215f)
        text(stream, font, record.dateOfBirth, PdfCoordinates.CHILD_DOB_TABLE_X, PdfCoordinates.CHILD_DOB_TABLE_Y, 8.4f, 24, 90f)

        text(stream, font, record.fatherName, PdfCoordinates.FATHER_NAME_MR_X, PdfCoordinates.FATHER_NAME_MR_Y, 8.4f, 46, 215f)
        text(stream, font, record.fatherName, PdfCoordinates.FATHER_NAME_EN_X, PdfCoordinates.FATHER_NAME_EN_Y, 8.4f, 46, 215f)
        text(stream, font, record.fatherAadhaar.toGroupedAadhaar(), PdfCoordinates.FATHER_AADHAAR_X, PdfCoordinates.FATHER_AADHAAR_Y, 8.4f, 24, 120f)

        text(stream, font, record.motherName, PdfCoordinates.MOTHER_NAME_MR_X, PdfCoordinates.MOTHER_NAME_MR_Y, 8.4f, 46, 215f)
        text(stream, font, record.motherName, PdfCoordinates.MOTHER_NAME_EN_X, PdfCoordinates.MOTHER_NAME_EN_Y, 8.4f, 46, 215f)
        text(stream, font, record.motherAadhaar.toGroupedAadhaar(), PdfCoordinates.MOTHER_AADHAAR_X, PdfCoordinates.MOTHER_AADHAAR_Y, 8.4f, 24, 120f)

        text(stream, font, record.placeOfBirth.ifBlank { address }, PdfCoordinates.CURRENT_ADDRESS_X, PdfCoordinates.CURRENT_ADDRESS_Y, 8.4f, 62, 215f)
        text(stream, font, address, PdfCoordinates.PERMANENT_ADDRESS_X, PdfCoordinates.PERMANENT_ADDRESS_Y, 8.4f, 62, 215f)
        text(stream, font, record.informantName.uppercase(), PdfCoordinates.INFORMANT_SIGNATURE_X, PdfCoordinates.INFORMANT_SIGNATURE_Y, 8.4f, 22, 90f)
    }

    private fun text(
        stream: PDPageContentStream,
        font: PDType0Font,
        value: String,
        x: Float,
        y: Float,
        size: Float,
        maxChars: Int,
        maxWidth: Float
    ) {
        val clean = value.trim().replace(Regex("""\s+"""), " ").take(maxChars)
        if (clean.isBlank()) return
        val fittedSize = fittedSize(font, clean, size, maxWidth)
        stream.beginText()
        stream.setFont(font, fittedSize)
        stream.newLineAtOffset(x, y)
        stream.showText(clean)
        stream.endText()
    }

    private fun fittedSize(font: PDType0Font, value: String, requestedSize: Float, maxWidth: Float): Float {
        val widthAtRequested = font.getStringWidth(value) / 1000f * requestedSize
        if (widthAtRequested <= maxWidth) return requestedSize
        return (requestedSize * maxWidth / widthAtRequested).coerceAtLeast(6.8f)
    }

    private fun today(): String {
        val calendar = java.util.Calendar.getInstance()
        return "%02d/%02d/%04d".format(
            calendar.get(java.util.Calendar.DAY_OF_MONTH),
            calendar.get(java.util.Calendar.MONTH) + 1,
            calendar.get(java.util.Calendar.YEAR)
        )
    }

    private fun String.toGroupedAadhaar(): String =
        filter(Char::isDigit).chunked(4).joinToString(" ").ifBlank { this }

    private fun BirthRecord.informantAge(): String = when {
        relation.contains("mother", ignoreCase = true) && motherAge.isNotBlank() -> motherAge
        relation.contains("आई") && motherAge.isNotBlank() -> motherAge
        relation.contains("father", ignoreCase = true) && fatherAge.isNotBlank() -> fatherAge
        relation.contains("वड") && fatherAge.isNotBlank() -> fatherAge
        fatherAge.isNotBlank() -> fatherAge
        else -> motherAge
    }

    private fun String.toLines(maxChars: Int, maxLines: Int): List<String> {
        val words = trim().replace(Regex("""\s+"""), " ").split(" ").filter { it.isNotBlank() }
        val lines = mutableListOf<String>()
        var current = ""
        for (word in words) {
            val candidate = if (current.isBlank()) word else "$current $word"
            if (candidate.length <= maxChars) {
                current = candidate
            } else {
                if (current.isNotBlank()) lines += current
                current = word
                if (lines.size == maxLines - 1) break
            }
        }
        if (current.isNotBlank() && lines.size < maxLines) lines += current
        return lines
    }

    private companion object {
        const val TEMPLATE_ASSET = "forms/birth_registration_form_v3.pdf"
        const val FONT_ASSET = "fonts/NotoSansDevanagari-Bold.ttf"
    }
}
