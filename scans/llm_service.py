import time
from openai import OpenAI
from django.conf import settings

# OpenAI প্যাকেজ ব্যবহার করে Google Gemini-তে কানেক্ট করা হচ্ছে
client = OpenAI(
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
    api_key=settings.GEMINI_API_KEY,
)

# আপনার API Key এর জন্য সঠিক মডেল
LLM_MODEL = "gemini-2.0-flash"


def _call_llm(system_prompt, user_prompt, max_output_tokens=800):
    """
    Gemini API কল করার জন্য common helper।
    """
    full_prompt = f"{system_prompt}\n\n{user_prompt}"

    # ম্যাক্সিমাম ৩ বার চেষ্টা করবে
    for attempt in range(3):
        try:
            response = client.chat.completions.create(
                model=LLM_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=max_output_tokens,
            )
            return response.choices[0].message.content
        except Exception as e:
            # যদি 429 (Rate Limit) এরর আসে, তবে ২০ সেকেন্ড অপেক্ষা করে আবার চেষ্টা করবে
            if "429" in str(e) and attempt < 2:
                time.sleep(20)
            else:
                raise Exception(f"Gemini API Error: {str(e)}")


def _build_case_context(scan):
    """
    একটা scan-এর এখন পর্যন্ত যা যা তথ্য জমা হয়েছে একটা common টেক্সট ব্লকে সাজায়।
    """
    analysis = scan.analysis
    review = getattr(scan, "radiologist_review", None)
    consultation = getattr(scan, "doctor_consultation", None)
    report = getattr(scan, "final_report", None)

    parts = [
        f"Scan type: {scan.scan_type}",
        f"AI classification: {analysis.classification} (confidence {analysis.confidence_score}%)",
    ]
    if analysis.tumor_area_percentage is not None:
        parts.append(
            f"Segmentation tumor area: {analysis.tumor_area_percentage}% of scan area"
        )
    if analysis.needs_review:
        parts.append(
            "Flag: classifier and segmentation results conflicted, manual review was required."
        )
    if review:
        parts.append(f"Radiologist review status: {review.status}")
        if review.corrected_classification:
            parts.append(
                f"Radiologist's corrected diagnosis: {review.corrected_classification}"
            )
        if review.observations:
            parts.append(f"Radiologist's observations: {review.observations}")
    if consultation:
        parts.append(
            f"Doctor's clinical assessment: {consultation.clinical_assessment}"
        )
        if consultation.treatment_recommendation:
            parts.append(
                f"Doctor's treatment recommendation: {consultation.treatment_recommendation}"
            )
    if report:
        parts.append(f"Final diagnosis: {report.final_diagnosis}")
        parts.append(f"Doctor's final summary: {report.summary}")
        parts.append(f"Final report status: {report.status}")

    return "\n".join(parts)


# ===========================================================================
# ১. Clinical Summarization
# ===========================================================================
def generate_clinical_summary(scan):
    context_text = _build_case_context(scan)
    system_prompt = (
        "তুমি একজন রেডিওলজি ক্লিনিক্যাল সহকারী। নিচের কেস ডেটা থেকে একজন "
        "radiologist বা doctor-এর জন্য সংক্ষিপ্ত, প্রফেশনাল ক্লিনিক্যাল সামারি "
        "লেখো (৩-৫ বাক্য)। স্ট্যান্ডার্ড মেডিক্যাল টার্মিনোলজি ব্যবহার করবে।"
    )
    return _call_llm(
        system_prompt,
        f"Case data:\n\n{context_text}\n\nএর একটা সংক্ষিপ্ত ক্লিনিক্যাল সামারি লেখো।",
    )


# ===========================================================================
# ২. Result Interpretation
# ===========================================================================
def interpret_ai_result(scan):
    analysis = scan.analysis
    context_parts = [
        f"Classification: {analysis.classification}",
        f"Confidence score: {analysis.confidence_score}%",
    ]
    if analysis.tumor_area_percentage is not None:
        context_parts.append(
            f"Segmentation tumor area: {analysis.tumor_area_percentage}%"
        )
    context_parts.append(f"Needs manual review flag: {analysis.needs_review}")
    context_text = "\n".join(context_parts)

    system_prompt = (
        "তুমি একজন AI রেডিওলজি সহকারী। classification এবং segmentation area-এর "
        "ক্লিনিক্যাল অর্থ ব্যাখ্যা করো। কখনোই নিজে থেকে চূড়ান্ত diagnosis দেবে না।"
    )
    return _call_llm(
        system_prompt,
        f"AI output:\n\n{context_text}\n\nএটা radiologist-এর জন্য ব্যাখ্যা করো।",
    )


# ===========================================================================
# ৩. Report Drafting
# ===========================================================================
def draft_final_report_text(scan):
    context_text = _build_case_context(scan)
    system_prompt = (
        "তুমি একজন মেডিকেল রিপোর্ট ড্রাফটিং সহকারী। নিচের কেস ডেটা থেকে একটা "
        "structured draft radiology/clinical report লেখো।"
    )
    return _call_llm(
        system_prompt, f"Case data:\n\n{context_text}\n\nএর ভিত্তিতে draft report লেখো।"
    )


# ===========================================================================
# ৪. Comparison & Progression
# ===========================================================================
def compare_scan_progression(current_scan, previous_scan):
    current_analysis = current_scan.analysis
    previous_analysis = previous_scan.analysis
    context_text = (
        f"Previous scan: Classification {previous_analysis.classification}, Tumor area {previous_analysis.tumor_area_percentage}%\n"
        f"Current scan: Classification {current_analysis.classification}, Tumor area {current_analysis.tumor_area_percentage}%"
    )
    system_prompt = (
        "একই রোগীর দুইটা scan-এর AI ফলাফল তুলনা করে progression ব্যাখ্যা করো।"
    )
    return _call_llm(
        system_prompt,
        f"{context_text}\n\nএই দুইটা scan-এর মধ্যে progression ব্যাখ্যা করো।",
    )


# ===========================================================================
# ৫. Medical Q&A
# ===========================================================================
def answer_medical_question(scan, question):
    context_text = _build_case_context(scan)
    system_prompt = (
        "তুমি একজন মেডিকেল তথ্য সহকারী। শুধু নিচের scan-এর রেকর্ড করা ডেটার ভিত্তিতে উত্তর দাও। "
        "ডেটার বাইরে কোনো নতুন diagnosis বা treatment পরামর্শ দেবে না।"
    )
    return _call_llm(
        system_prompt,
        f"Scan-এর রেকর্ড করা তথ্য:\n\n{context_text}\n\nপ্রশ্ন: {question}",
    )


# ===========================================================================
# ৬. Follow-up Recommendations
# ===========================================================================
def suggest_follow_up_recommendations(scan):
    context_text = _build_case_context(scan)
    system_prompt = (
        "কেস ডেটার ভিত্তিতে doctor-কে ৩-৫টা সম্ভাব্য follow-up পদক্ষেপ সাজেস্ট করো।"
    )
    return _call_llm(
        system_prompt,
        f"Case data:\n\n{context_text}\n\nসম্ভাব্য follow-up পদক্ষেপ সাজেস্ট করো।",
    )


# ===========================================================================
# ৭. Patient Friendly Explanation
# ===========================================================================
def generate_patient_friendly_explanation(scan):
    context_text = _build_case_context(scan)
    system_prompt = (
        "তুমি একজন সহায়ক মেডিকেল কমিউনিকেশন সহকারী। একজন রোগীকে তার ব্রেইন MRI "
        "রিপোর্ট বাংলা ভাষায়, সহজ ও অ-প্রযুক্তিগত ভাষায় ব্যাখ্যা করবে। "
        "ভয় না দেখিয়ে, সহানুভূতিশীল ও শান্ত টোনে ব্যাখ্যা করো।"
    )
    return _call_llm(
        system_prompt,
        f"এই রোগীর MRI রিপোর্টের তথ্য:\n\n{context_text}\n\nএটা রোগীর জন্য সহজ ভাষায় ব্যাখ্যা করে দাও।",
    )
