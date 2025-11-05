document.getElementById("saveBtn").addEventListener("click", async () => {
    // Get the active tab
    let [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  
    // Execute script in tab to grab the full HTML
    const [{ result }] = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: () => document.documentElement.outerHTML
    });
  
    // Send to  backend
    await fetch("http://localhost:8000/api/save-job", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        url: tab.url,
        html: result
      })
    });
  
    alert("Job page sent to server!");
  });
  