/**
 * Cookie-based Authentication utilities with automatic expiration
 */
window.AuthUtils = (function() {
    
    // Cookie utility functions
    function getCookie(name) {
        console.log('AuthUtils: All cookies =', document.cookie);
        const value = `; ${document.cookie}`;
        const parts = value.split(`; ${name}=`);
        if (parts.length === 2) {
            let cookieValue = parts.pop().split(';').shift();
            // Remove quotes if present
            if (cookieValue.startsWith('"') && cookieValue.endsWith('"')) {
                cookieValue = cookieValue.slice(1, -1);
            }
            console.log(`AuthUtils: Found cookie ${name} =`, cookieValue);
            return cookieValue;
        }
        console.log(`AuthUtils: Cookie ${name} not found`);
        return null;
    }
    
    function setCookie(name, value, hours) {
        const expires = new Date(Date.now() + hours * 60 * 60 * 1000).toUTCString();
        document.cookie = `${name}=${value}; expires=${expires}; path=/; samesite=lax`;
    }
    
    function deleteCookie(name) {
        document.cookie = `${name}=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;`;
    }
    
    function getStoredToken() {
        const token = getCookie('token');
        console.log('AuthUtils: getStoredToken =', !!token);
        return token;
    }
    
    function getStoredUser() {
        const userData = getCookie('user_data');
        console.log('\n=== AUTH UTILS DEBUG ===');
        console.log('AuthUtils: raw user_data cookie =', userData);
        if (userData) {
            try {
                // Handle URL decoding if needed
                const cleanData = decodeURIComponent(userData);
                console.log('AuthUtils: URL decoded =', cleanData);
                const decoded = atob(cleanData);  // Base64 decode
                console.log('AuthUtils: Base64 decoded =', decoded);
                const parsed = JSON.parse(decoded);
                console.log('AuthUtils: Final parsed user_data =', parsed);
                console.log('AuthUtils: Role from parsed =', parsed.role);
                console.log('AuthUtils: Candidate ID from parsed =', parsed.candidate_id);
                console.log('=== AUTH UTILS END ===\n');
                return parsed;
            } catch (e) {
                console.log('AuthUtils: Base64 decode failed:', e);
                // Try parsing without base64 decode as fallback
                try {
                    const parsed = JSON.parse(userData);
                    console.log('AuthUtils: Direct parse success =', parsed);
                    console.log('=== AUTH UTILS END ===\n');
                    return parsed;
                } catch (e2) {
                    console.log('AuthUtils: Complete parsing failure:', e2);
                    console.log('=== AUTH UTILS END ===\n');
                    return {};
                }
            }
        }
        console.log('AuthUtils: No user_data cookie found');
        console.log('=== AUTH UTILS END ===\n');
        return {};
    }
    
    function getStoredCandidateId() {
        const user = getStoredUser();
        return user.candidate_id;
    }
    
    function clearAuthData() {
        deleteCookie('token');
        deleteCookie('user_data');
    }
    
    function redirectToLogin() {
        clearAuthData();
        window.location.href = '/login';
    }
    
    async function authenticatedFetch(url, options = {}) {
        const token = getStoredToken();
        
        if (!token) {
            redirectToLogin();
            return Promise.reject(new Error('No token'));
        }
        
        // Add auth header as fallback (cookies are sent automatically)
        const headers = {
            'Authorization': `Bearer ${token}`,
            ...options.headers
        };
        
        try {
            const response = await fetch(url, { 
                ...options, 
                headers,
                credentials: 'include'  // Include cookies in request
            });
            
            // Handle 401 responses
            if (response.status === 401) {
                alert('Your session has expired. Please log in again.');
                redirectToLogin();
                throw new Error('Unauthorized');
            }
            
            return response;
        } catch (error) {
            if (error.message === 'Unauthorized') {
                throw error;
            }
            throw error;
        }
    }
    
    function initAuthCheck() {
        // Check if we have auth cookies
        const token = getStoredToken();
        const user = getStoredUser();
        
        // If no token/user data, cookies have expired or don't exist
        if (!token || !user.candidate_id) {
            return false;
        }
        
        return true;
    }
    
    // Logout function
    async function logout() {
        try {
            await fetch('/logout', { 
                method: 'POST',
                credentials: 'include'
            });
        } catch (e) {
            // Even if request fails, clear local cookies
        }
        clearAuthData();
        window.location.href = '/login';
    }
    
    return {
        getStoredToken,
        getStoredUser,
        getStoredCandidateId,
        clearAuthData,
        redirectToLogin,
        authenticatedFetch,
        initAuthCheck,
        logout,
        getCookie,
        setCookie,
        deleteCookie
    };
})();