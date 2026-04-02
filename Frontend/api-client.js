// ==========================================
// KalingaSync AI | Global API Client
// ==========================================

// 🚀 ENTERPRISE SECURITY: Global XSS Sanitization Engine
function escapeHTML(str) {
    if (str === null || str === undefined) return '';
    return String(str).replace(/[&<>'"]/g, match => {
        const escapeMap = { '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' };
        return escapeMap[match];
    });
}

// 🚀 ROBUSTNESS: Unified Fetch Wrapper for Absolute Error Handling
async function safeFetch(payload, apiRouteOverride = null) {
    // 🚀 ARCHITECT FIX: Smart Context-Aware Routing
    // Automatically determine which API to hit based on the central config and current page
    let API_ROUTE = '';
    
    if (apiRouteOverride) {
        API_ROUTE = apiRouteOverride;
    } else if (typeof KalingaConfig !== 'undefined') {
        // If we are on the admin page, use ADMIN_API, otherwise use EMPLOYEE_API
        API_ROUTE = window.location.pathname.includes('admin.html') 
            ? KalingaConfig.ADMIN_API 
            : KalingaConfig.EMPLOYEE_API;
    } else {
        throw new Error("KalingaConfig is missing. Cannot resolve API routes.");
    }

    if (!API_ROUTE) {
        throw new Error("Critical Configuration Error: API Route is empty.");
    }

    // 🚀 SECURITY UPGRADE: Extract and validate the JWT from session storage
    let idToken = '';
    try {
        const sessionData = JSON.parse(sessionStorage.getItem('kalinga_session') || '{}');
        
        // 🛡️ SECURITY FIX 1: Strict type validation prevents Header Injection & Type Juggling
        if (sessionData.idToken && typeof sessionData.idToken === 'string') {
            idToken = sessionData.idToken;
        }
    } catch (e) { 
        console.warn("Session token read failed."); 
    }

    // 🛡️ Build headers dynamically, injecting the secure token if present
    const headers = { 
        'Content-Type': 'application/json'
        // Note: X-Requested-With removed to prevent strict CORS blocking on AWS API Gateway
    };
    if (idToken) headers['Authorization'] = idToken;

    let res;
    try {
        res = await fetch(API_ROUTE, { 
            method: 'POST', 
            headers: headers, 
            body: JSON.stringify(payload) 
        });
    } catch (err) {
        throw new Error(`Network Error: Failed to reach the server at ${API_ROUTE}. Ensure your API Gateway is deployed and CORS is configured.`);
    }
    
    // 🚀 SECURITY UPGRADE: Immediately catch 401 Unauthorized errors from API Gateway
    if (res.status === 401) {
        sessionStorage.removeItem('kalinga_session');
        
        // 🛡️ SECURITY FIX 2: Non-blocking enterprise UI handling instead of alert()
        if (typeof showNotif === 'function') {
            showNotif("Security Session Expired. Please sign in again.", true);
        }
        
        // Graceful redirect to avoid thread freezing
        setTimeout(() => { window.location.href = "index.html"; }, 1500);
        throw new Error("HTTP 401 Unauthorized");
    }
    
    const rawText = await res.text();
    let data;
    try { 
        data = JSON.parse(rawText); 
    } catch(e) { 
        throw new Error(`Backend crashed. Check Lambda logs.`); 
    }
    
    // 🛡️ SECURITY FIX 3: Sanitize backend error payloads to prevent Reflected XSS
    if (!res.ok) {
        const errorMsg = data.error || data.message || `Server Error: ${res.status}`;
        throw new Error(escapeHTML(errorMsg));
    }

    return data;
}