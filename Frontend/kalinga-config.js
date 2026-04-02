// 🛡️ SECURITY FIX: Object.freeze() locks the object in memory, preventing runtime tampering
const KalingaConfig = Object.freeze({
    // 🚨 1. CENTRALIZED API URLS
    EMPLOYEE_API: "https://9qjsexkno0.execute-api.us-east-1.amazonaws.com/employee",
    ADMIN_API: "https://js0rrpmm50.execute-api.us-east-1.amazonaws.com/admin", 

    // 🔐 2. COGNITO AUTHENTICATION CREDENTIALS
    USER_POOL_ID: "us-east-1_FoKvQRJB6", 
    CLIENT_ID: "7q1r8bhvdkgbvl9qf0jd4me5oi",       

    // 🏢 3. SINGLE SOURCE OF TRUTH: DEPARTMENTS
    // 🛡️ SECURITY FIX: Deep freezing the arrays to prevent UI manipulation
    DEPARTMENTS: Object.freeze([
        "Cloud Engineering",
        "Data Science",
        "Cybersecurity",
        "HR & Operations",
        "Executive Management",
        "Sales & Marketing",
        "Software Engineering",
        "CEO"
    ]),

    // 🌍 4. SINGLE SOURCE OF TRUTH: COUNTRY CODES
    COUNTRY_CODES: Object.freeze([
        { code: "+91", label: "🇮🇳 +91" },
        { code: "+1", label: "🇺🇸 +1" },
        { code: "+44", label: "🇬🇧 +44" },
        { code: "+61", label: "🇦🇺 +61" }
    ]),

    // 🛠️ 5. THE SMART AUTO-BUILDER
    populateDropdowns: function(elementIds, dataType) {
        elementIds.forEach(id => {
            const selectEl = document.getElementById(id);
            if (!selectEl) return;

            selectEl.innerHTML = ''; 

            if (dataType === 'departments') {
                selectEl.innerHTML = '<option value="" disabled selected>Select Department...</option>';
                this.DEPARTMENTS.forEach(dept => {
                    const opt = document.createElement('option');
                    opt.value = dept; opt.innerText = dept;
                    selectEl.appendChild(opt);
                });
            } 
            else if (dataType === 'countries') {
                this.COUNTRY_CODES.forEach(country => {
                    const opt = document.createElement('option');
                    opt.value = country.code; opt.innerText = country.label;
                    selectEl.appendChild(opt);
                });
            }
        });
    }
});