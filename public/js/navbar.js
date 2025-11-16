(function renderNavbar() {
  const root = document.getElementById('navbar-root');
  if (!root) return;

  // Wait for AuthUtils to be available
  if (!window.AuthUtils) {
    setTimeout(renderNavbar, 100);
    return;
  }
  
  // Read from cookies using AuthUtils
  const token = window.AuthUtils.getStoredToken();
  const candidateId = window.AuthUtils.getStoredCandidateId();
  const stored = window.AuthUtils.getStoredUser();
  const role = (stored.role || 'candidate').toLowerCase();
  
  // DEBUG: Log what we're reading
  console.log('\n=== NAVBAR DEBUG START ===');
  console.log('NAVBAR DEBUG: All cookies =', document.cookie);
  console.log('NAVBAR DEBUG: Token found =', !!token);
  console.log('NAVBAR DEBUG: Token value =', token ? token.substring(0, 20) + '...' : 'null');
  console.log('NAVBAR DEBUG: Raw stored object =', stored);
  console.log('NAVBAR DEBUG: Candidate ID =', candidateId);
  console.log('NAVBAR DEBUG: Role =', role);
  console.log('NAVBAR DEBUG: Role type =', typeof role);
  console.log('NAVBAR DEBUG: Current page =', window.location.pathname);
  console.log('=== NAVBAR DEBUG END ===\n');

  const brandHref = token && candidateId ? `/${candidateId}/home` : `/home`;
  const homeHref = brandHref;
  const left = `<a id="brand-link" href="${brandHref}" class="text-xl font-bold text-blue-700">Hiring Agent</a>`;

  let right = '';
  console.log('NAVBAR: Checking token...', !!token);
  if (token) {
    console.log('NAVBAR: User is logged in, role:', role);
    console.log('NAVBAR: candidateId:', candidateId);
    console.log('NAVBAR: stored object:', stored);
    if (role === 'hr') {
      console.log('NAVBAR: HR user detected');
      if (candidateId) {
        console.log('NAVBAR: HR user has candidateId, showing full navbar');
        right = `
        <a href="${homeHref}" class="text-gray-700 hover:text-blue-700">Home</a>
        <a href="/${candidateId}/create_process" class="text-gray-700 hover:text-blue-700">Create Process</a>
        <a href="/${candidateId}/show_all_processes" class="text-gray-700 hover:text-blue-700">Your Processes</a>
        <button id="logoutBtn" class="text-gray-700 hover:text-blue-700">Logout</button>
      `;
      } else {
        console.log('NAVBAR: HR user has NO candidateId, showing minimal navbar');
        right = `
        <a href="${homeHref}" class="text-gray-700 hover:text-blue-700">Home</a>
        <button id="logoutBtn" class="text-gray-700 hover:text-blue-700">Logout</button>
      `;
      }
    } else {
      if (candidateId) {
        right = `
        <a href="${homeHref}" class="text-gray-700 hover:text-blue-700">Home</a>
        <a href="/${candidateId}/profile" class="text-gray-700 hover:text-blue-700">Profile</a>
        <a href="/${candidateId}/apply" class="text-gray-700 hover:text-blue-700">Apply for Hiring</a>
        <a href="/${candidateId}/applied-processes" class="text-gray-700 hover:text-blue-700">Applied Processes</a>
        <button id="logoutBtn" class="text-gray-700 hover:text-blue-700">Logout</button>
      `;
      } else {
        right = `
        <a href="${homeHref}" class="text-gray-700 hover:text-blue-700">Home</a>
        <button id="logoutBtn" class="text-gray-700 hover:text-blue-700">Logout</button>
      `;
      }
    }
  } else {
    console.log('NAVBAR: User is NOT logged in - showing guest navbar');
    right = `
      <a href="/home" class="text-gray-700 hover:text-blue-700">Home</a>
      <a href="/login" class="text-gray-700 hover:text-blue-700">Sign In</a>
      <a href="/signup" class="text-gray-700 hover:text-blue-700">Sign Up</a>
    `;
  }

  console.log('NAVBAR: Final navbar HTML:', right);

  root.innerHTML = `
    <nav class="bg-white border-b border-gray-200">
      <div class="max-w-6xl mx-auto px-4">
        <div class="flex justify-between h-16 items-center">
          ${left}
          <div class="flex gap-6">${right}</div>
        </div>
      </div>
    </nav>
  `;

  const logoutBtn = document.getElementById('logoutBtn');
  if (logoutBtn) {
    logoutBtn.addEventListener('click', async () => {
      await window.AuthUtils.logout();
    });
  }
})();


