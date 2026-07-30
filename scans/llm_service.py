from django.conf import settings
from google import genai
from google.genai import types

_client = None

GEMINI_MODEL = "gemini-2.5-flash"


def get_client():
    global _client
    if _client is None:
        _client = genai.Client(api_key=settings.GEMINI_API_KEY)
    return _client


def _call_gemini(system_prompt, user_prompt, max_output_tokens=800):
    """
    Gemini API কল করার জন্য common helper -- প্রতিটা LLM ফাংশনে একই
    client/config বয়লারপ্লেট বারবার না লিখে এখানে একবার রাখা হয়েছে।
    """
    client = get_client()
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=user_prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            max_output_tokens=max_output_tokens,
        ),
    )
    return response.text


def _build_case_context(scan):
    """
    একটা scan-এর এখন পর্যন্ত যা যা তথ্য জমা হয়েছে (AI analysis, radiologist
    review, doctor consultation, final report -- যেগুলো আছে) একটা common
    টেক্সট ব্লকে সাজায়। প্রায় প্রতিটা LLM ফাংশনেরই এই context লাগে, তাই এখানে
    একবার লেখা হয়েছে -- কোনো workflow ধাপ (যেমন consultation) এখনো না হলে
    সেই অংশ চুপচাপ বাদ পড়ে যায়, error দেয় না।
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
    """
    Radiologist/Doctor-এর জন্য: একটা scan-এ এখন পর্যন্ত যা যা রেকর্ড হয়েছে তার
    সংক্ষিপ্ত ক্লিনিক্যাল সামারি -- পুরো কেস ফাইল খুলে পড়ার বদলে ৩-৪ লাইনে
    দ্রুত ওভারভিউ পাওয়ার জন্য (workflow-এর যেকোনো ধাপে কল করা যায়)।
    """
    context_text = _build_case_context(scan)

    system_prompt = (
        "তুমি একজন রেডিওলজি ক্লিনিক্যাল সহকারী। নিচের কেস ডেটা থেকে একজন "
        "radiologist বা doctor-এর জন্য সংক্ষিপ্ত, প্রফেশনাল ক্লিনিক্যাল সামারি "
        "লেখো (৩-৫ বাক্য)। স্ট্যান্ডার্ড মেডিক্যাল টার্মিনোলজি ব্যবহার করবে। "
        "যা ডেটাতে নেই তা অনুমান করে যোগ করবে না -- শুধু যা রেকর্ড করা আছে "
        "তার সংক্ষিপ্তসার দেবে।"
    )
    return _call_gemini(
        system_prompt,
        f"Case data:\n\n{context_text}\n\nএর একটা সংক্ষিপ্ত ক্লিনিক্যাল সামারি লেখো।",
        max_output_tokens=400,
    )


# ===========================================================================
# ২. Result Interpretation
# ===========================================================================
def interpret_ai_result(scan):
    """
    Radiologist-এর জন্য: AI classification/segmentation ফলাফল ও confidence
    score-এর ক্লিনিক্যাল তাৎপর্য ব্যাখ্যা করে -- বিশেষ করে needs_review flag
    উঠলে কেন উঠলো এবং radiologist-এর কী বিবেচনা করা উচিত সেটা বলে।
    """
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
        "তুমি একজন AI রেডিওলজি সহকারী যে radiologist-কে model output বুঝতে সাহায্য করে। "
        "classification, confidence score এবং segmentation area-এর ক্লিনিক্যাল অর্থ "
        "ব্যাখ্যা করো -- যেমন এই confidence level কতটা নির্ভরযোগ্য বিবেচনা করা উচিত, "
        "এবং needs_review flag থাকলে দুই মডেলের মধ্যে কী দ্বন্দ্ব হয়েছে ও কেন সেটা "
        "ম্যানুয়ালি যাচাই করা দরকার। কখনোই নিজে থেকে চূড়ান্ত diagnosis দেবে না -- "
        "এটা শুধু AI output ব্যাখ্যা, নতুন ক্লিনিক্যাল সিদ্ধান্ত না।"
    )
    return _call_gemini(
        system_prompt,
        f"AI output:\n\n{context_text}\n\nএটা radiologist-এর জন্য ব্যাখ্যা করো।",
        max_output_tokens=500,
    )


# ===========================================================================
# ৩. Report Drafting
# ===========================================================================
def draft_final_report_text(scan):
    """
    Doctor-এর জন্য: doctor consultation হয়ে যাওয়ার পর, final report-এর
    summary ফিল্ডে বসানোর জন্য একটা draft তৈরি করে দেয় (Findings / Impression /
    Recommendation কাঠামোতে)। doctor এটা নিজের মতো edit করে তারপর
    generate-report endpoint-এ পাঠাবে -- এটা শুধু starting point, চূড়ান্ত না।
    """
    context_text = _build_case_context(scan)

    system_prompt = (
        "তুমি একজন মেডিকেল রিপোর্ট ড্রাফটিং সহকারী। নিচের কেস ডেটা থেকে একটা "
        "structured draft radiology/clinical report লেখো, এই তিনটা section দিয়ে:\n"
        "Findings: (AI ও radiologist যা পেয়েছে)\n"
        "Impression: (সামগ্রিক ক্লিনিক্যাল উপসংহার)\n"
        "Recommendation: (পরবর্তী পদক্ষেপ, যদি doctor-এর treatment recommendation থাকে)\n\n"
        "এটা শুধু একটা draft -- doctor এটা review করে edit করবে, তাই স্পষ্টভাবে "
        "জানানো তথ্যের বাইরে নতুন কোনো diagnosis বা treatment নিজে থেকে যোগ করবে না।"
    )
    return _call_gemini(
        system_prompt,
        f"Case data:\n\n{context_text}\n\nএর ভিত্তিতে draft report লেখো।",
        max_output_tokens=700,
    )


# ===========================================================================
# ৪. Comparison & Progression
# ===========================================================================
def compare_scan_progression(current_scan, previous_scan):
    """
    একই patient-এর দুইটা scan (current vs আগের কোনো scan) তুলনা করে tumor
    area/classification-এ কী পরিবর্তন হয়েছে তা ব্যাখ্যা করে -- radiologist/doctor
    কে progression বোঝার জন্য (কল করার আগে view-তে নিশ্চিত করতে হবে দুটো scan-ই
    একই patient-এর)।
    """
    current_analysis = current_scan.analysis
    previous_analysis = previous_scan.analysis

    context_text = (
        f"Previous scan ({previous_scan.uploaded_at.date()}):\n"
        f"  Classification: {previous_analysis.classification} "
        f"(confidence {previous_analysis.confidence_score}%)\n"
        f"  Tumor area: {previous_analysis.tumor_area_percentage}%\n\n"
        f"Current scan ({current_scan.uploaded_at.date()}):\n"
        f"  Classification: {current_analysis.classification} "
        f"(confidence {current_analysis.confidence_score}%)\n"
        f"  Tumor area: {current_analysis.tumor_area_percentage}%"
    )

    system_prompt = (
        "তুমি একজন রেডিওলজি progression-analysis সহকারী। একই রোগীর দুইটা scan-এর "
        "(আগের এবং বর্তমান) AI ফলাফল তুলনা করে বলো: tumor area/classification "
        "বেড়েছে, কমেছে, নাকি স্থিতিশীল আছে -- এবং এই পরিবর্তনের সাধারণ ক্লিনিক্যাল "
        "তাৎপর্য কী হতে পারে radiologist/doctor-এর জন্য। সংখ্যার বাইরে কোনো "
        "নতুন diagnosis নিজে থেকে করবে না, শুধু trend ব্যাখ্যা করো।"
    )
    return _call_gemini(
        system_prompt,
        f"{context_text}\n\nএই দুইটা scan-এর মধ্যে progression ব্যাখ্যা করো।",
        max_output_tokens=500,
    )


# ===========================================================================
# ৫. Medical Q&A
# ===========================================================================
def answer_medical_question(scan, question):
    """
    scan-এর ডেটার ভিত্তিতে (শুধু authorized ইউজারের নিজের/দায়িত্বে থাকা scan
    -- permission view-তে চেক হয়) একটা নির্দিষ্ট প্রশ্নের উত্তর দেয়। শুধু এই
    scan-এ যা রেকর্ড করা আছে তার ভিত্তিতে উত্তর দেয়, বাইরের কিছু অনুমান করে না।
    """
    context_text = _build_case_context(scan)

    system_prompt = (
        "তুমি একজন মেডিকেল তথ্য সহকারী। তোমাকে একজন রোগী, radiologist, বা "
        "doctor প্রশ্ন করছে -- শুধু নিচের scan-এর রেকর্ড করা ডেটার ভিত্তিতে "
        "উত্তর দাও। এই ডেটার বাইরে কোনো নতুন diagnosis, treatment পরামর্শ, বা "
        "অনুমান করবে না -- ডেটাতে উত্তর না থাকলে স্পষ্টভাবে বলো যে এই তথ্য "
        "রেকর্ডে নেই এবং ডাক্তারের সাথে সরাসরি কথা বলতে বলো। উত্তর সংক্ষিপ্ত ও "
        "স্পষ্ট রাখবে।"
    )
    return _call_gemini(
        system_prompt,
        f"Scan-এর রেকর্ড করা তথ্য:\n\n{context_text}\n\nপ্রশ্ন: {question}",
        max_output_tokens=500,
    )


# ===========================================================================
# ৬. Follow-up Recommendations
# ===========================================================================
def suggest_follow_up_recommendations(scan):
    """
    Doctor-এর জন্য: final report/treatment recommendation-এর ভিত্তিতে সম্ভাব্য
    follow-up টেস্ট বা পরবর্তী পদক্ষেপের একটা সাজেশন-লিস্ট তৈরি করে -- এটা
    doctor review/approve করার আগে শুধুই একটা সহায়ক সাজেশন, চূড়ান্ত মেডিকেল
    পরামর্শ না (doctor নিজে যাচাই করে এটা গ্রহণ/বাতিল/সংশোধন করবে)।
    """
    context_text = _build_case_context(scan)

    system_prompt = (
        "তুমি একজন ক্লিনিক্যাল follow-up planning সহকারী। নিচের কেস ডেটার "
        "ভিত্তিতে doctor-কে কিছু সম্ভাব্য follow-up পদক্ষেপ সাজেস্ট করো (যেমন: "
        "পরবর্তী ইমেজিং-এর সময়সীমা, কোন specialist-এর কাছে রেফার করা যেতে "
        "পারে, কী ধরনের মনিটরিং দরকার হতে পারে) -- বুলেট পয়েন্ট আকারে, ৩-৫টা। "
        "এগুলো শুধু সাজেশন, চূড়ান্ত সিদ্ধান্ত না -- উত্তরের শুরুতে স্পষ্ট করে দাও যে "
        "এই সাজেশনগুলো doctor-এর নিজস্ব ক্লিনিক্যাল বিচারের বিকল্প না, শুধু সহায়ক।"
    )
    return _call_gemini(
        system_prompt,
        f"Case data:\n\n{context_text}\n\nসম্ভাব্য follow-up পদক্ষেপ সাজেস্ট করো।",
        max_output_tokens=500,
    )


# ===========================================================================
# ৭. Patient Friendly Explanation
# ===========================================================================
def generate_patient_friendly_explanation(scan):
    """
    একটা scan-এর AI analysis, radiologist review, doctor consultation ও
    final report থেকে patient-বান্ধব সহজ ভাষায় ব্যাখ্যা তৈরি করে (Gemini API দিয়ে)।

    শুধু approved final report থাকা scan-এর জন্যই এটা কল করা উচিত (view-তে চেক করা হয়)।
    """
    context_text = _build_case_context(scan)

    system_prompt = (
        "তুমি একজন সহায়ক মেডিকেল কমিউনিকেশন সহকারী। একজন রোগীকে তার ব্রেইন MRI "
        "রিপোর্ট বাংলা ভাষায়, সহজ ও অ-প্রযুক্তিগত ভাষায় ব্যাখ্যা করবে। "
        "ভয় না দেখিয়ে, সহানুভূতিশীল ও শান্ত টোনে ব্যাখ্যা করো, কিন্তু সৎ থেকো -- "
        "তথ্য লুকিয়ো না বা কম করে দেখিও না। "
        "গুরুত্বপূর্ণ: তুমি নিজে থেকে কোনো নতুন মেডিকেল পরামর্শ, ডায়াগনসিস, বা চিকিৎসা "
        "সুপারিশ যোগ করবে না -- শুধু ডাক্তার ও রেডিওলজিস্ট যা বলেছেন সেটাই সহজ ভাষায় "
        "পুনরায় ব্যাখ্যা করবে। উত্তরের শেষে অবশ্যই মনে করিয়ে দেবে যে বিস্তারিত প্রশ্ন বা "
        "উদ্বেগের জন্য রোগীর উচিত তার ডাক্তারের সাথে সরাসরি কথা বলা।"
    )
    return _call_gemini(
        system_prompt,
        (
            f"এই রোগীর MRI রিপোর্টের তথ্য:\n\n{context_text}\n\n"
            "এটা রোগীর জন্য সহজ, বোধগম্য ভাষায় ব্যাখ্যা করে দাও।"
        ),
        max_output_tokens=800,
    )
