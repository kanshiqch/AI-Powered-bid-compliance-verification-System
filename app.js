let currentDashboardData = null;
let sessionVendorBids = [];
let currentSelections = [];

document.addEventListener('DOMContentLoaded', () => {
  checkSession();

  // Register Logout Event Listener
  document.getElementById('btn-logout').addEventListener('click', () => {
    localStorage.removeItem('gem_username');
    localStorage.removeItem('gem_role');
    localStorage.removeItem('gem_name');
    localStorage.removeItem('gem_org');
    localStorage.removeItem('gem_acknowledged');
    checkSession();
  });

  // Portal Switcher Logic
  const tabGovt = document.getElementById('tab-govt');
  const tabVendor = document.getElementById('tab-vendor');
  const viewGovt = document.getElementById('govt-dashboard');
  const viewVendor = document.getElementById('vendor-dashboard');

  tabGovt.addEventListener('click', () => {
    tabGovt.classList.add('active');
    tabVendor.classList.remove('active');
    viewGovt.classList.add('active');
    viewVendor.classList.remove('active');
    // Redraw D3 graph to match active dimensions
    const activeSubtab = document.querySelector('.subtab-btn.active');
    if (activeSubtab && activeSubtab.id === 'subtab-collusion' && currentDashboardData && currentDashboardData.graph_data) {
      renderGNNGraph(currentDashboardData.graph_data);
    }
  });

  tabVendor.addEventListener('click', () => {
    tabVendor.classList.add('active');
    tabGovt.classList.remove('active');
    viewVendor.classList.add('active');
    viewGovt.classList.remove('active');
  });

  // Subtabs navigation toggle logic
  const subtabs = ['overview', 'checklist', 'collusion', 'recommendations', 'alerts'];
  subtabs.forEach(tab => {
    const btn = document.getElementById(`subtab-${tab}`);
    if (btn) {
      btn.addEventListener('click', () => {
        subtabs.forEach(t => {
          document.getElementById(`subtab-${t}`).classList.remove('active');
          document.getElementById(`panel-${t}`).classList.remove('active');
        });
        btn.classList.add('active');
        document.getElementById(`panel-${tab}`).classList.add('active');
        
        if (tab === 'collusion' && currentDashboardData && currentDashboardData.graph_data) {
          setTimeout(() => {
            renderGNNGraph(currentDashboardData.graph_data);
          }, 100);
        }
      });
    }
  });

  // Drag and Drop Upload Listeners
  const dropzone = document.getElementById('upload-dropzone');
  const fileInput = document.getElementById('bid-file-input');

  dropzone.addEventListener('click', () => fileInput.click());

  dropzone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropzone.classList.add('dragover');
  });

  dropzone.addEventListener('dragleave', () => {
    dropzone.classList.remove('dragover');
  });

  dropzone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropzone.classList.remove('dragover');
    const files = e.dataTransfer.files;
    if (files.length > 0) {
      handleBidUpload(files[0]);
    }
  });

  fileInput.addEventListener('change', (e) => {
    if (e.target.files.length > 0) {
      handleBidUpload(e.target.files[0]);
    }
  });

  document.getElementById('btn-reseed').addEventListener('click', async () => {
    const btn = document.getElementById('btn-reseed');
    btn.disabled = true;
    btn.innerHTML = '⏳ Running AI Audit...';
    try {
      await fetch('/api/demo/seed', { method: 'POST' });
      await fetchDashboardData();
    } catch (e) {
      console.error('Error re-running audit:', e);
    } finally {
      btn.disabled = false;
      btn.innerHTML = '🔄 Re-Run AI Audit Pipeline';
    }
  });

  document.getElementById('close-modal').addEventListener('click', () => {
    document.getElementById('audit-modal').style.display = 'none';
  });

  document.getElementById('close-email-modal').addEventListener('click', () => {
    document.getElementById('email-modal').style.display = 'none';
  });

  // Add chatbot enter-key event listener
  const chatInput = document.getElementById('chat-input');
  if (chatInput) {
    chatInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        sendChatMessage();
      }
    });
  }
});


async function fetchDashboardData() {
  try {
    const res = await fetch('/api/dashboard/stats');
    const data = await res.json();
    currentDashboardData = data;

    // Update Metrics
    document.getElementById('stat-total').textContent = data.total_bids;
    document.getElementById('stat-compliant').textContent = data.compliant_bids;
    document.getElementById('stat-review').textContent = data.review_needed_bids;
    document.getElementById('stat-rejected').textContent = data.rejected_bids;
    document.getElementById('stat-cartels').textContent = data.flagged_cartels;

    // Populate Table
    renderBidsTable(data.bids);

    // Populate Document Studio Chips
    renderDocumentChips(data.bids);

    // Render D3 GNN Graph
    if (data.graph_data) {
      renderGNNGraph(data.graph_data);
      renderCartelAlerts(data.graph_data.detected_cartels);
    }

    // Render system console log events
    if (data.recent_logs) {
      renderTerminalLogs(data.recent_logs);
    }

    // Seed vendor session bids list with the parsed default bids if empty
    if (sessionVendorBids.length === 0 && data.bids && data.bids.length > 0) {
      sessionVendorBids = [...data.bids];
      renderSessionHistory();
      renderVendorReport(sessionVendorBids[0]);
    }
    
    // Fetch and populate SQLite selection history table
    await fetchSelectionHistory();

    // Populate and fetch the upgraded compliance matrices
    populateBidSelectors(data.bids);
    fetchDuplicateBids();
    fetchAIRecommendations();
    fetchExpiryAlerts();
  } catch (err) {
    console.error('Failed to fetch dashboard stats:', err);
  }
}

function renderBidsTable(bids) {
  const tbody = document.getElementById('bids-table-body');
  tbody.innerHTML = '';

  bids.forEach(bid => {
    const tr = document.createElement('tr');
    
    let statusClass = 'green';
    let statusIcon = '🟢 PASS';
    if (bid.overall_status === 'YELLOW') {
      statusClass = 'yellow';
      statusIcon = '🟡 REVIEW';
    } else if (bid.overall_status === 'RED') {
      statusClass = 'red';
      statusIcon = '🔴 REJECTED';
    }

    const v = bid.vendor_details || {};
    const pdfLink = v.pdf_filename ? `/sample-pdfs/${v.pdf_filename}` : '#';

    const selectButtonOrBadge = bid.selected 
      ? `<span class="status-selected-badge">🏆 Selected</span>`
      : `<button class="btn btn-secondary btn-sm btn-select" onclick="selectBid('${bid.bid_id}')">🏆 Select</button>`;

    tr.innerHTML = `
      <td><span class="status-tag ${statusClass}">${statusIcon}</span></td>
      <td><code class="font-mono">${bid.bid_id}</code></td>
      <td><strong>${bid.vendor_name}</strong></td>
      <td><span class="score-pill" style="color: ${getScoreColor(bid.overall_score)}">${bid.overall_score}%</span></td>
      <td><small>${v.gst_number || 'N/A'}</small></td>
      <td><small>₹${v.turnover_lakhs || 0}L | ISO ${v.iso_expiry_year || 'N/A'}</small></td>
      <td>
        <button class="btn btn-secondary btn-sm" onclick="openAuditModal('${bid.bid_id}')">🔍 Inspect</button>
        <a href="${pdfLink}" target="_blank" class="btn btn-secondary btn-sm" style="text-decoration:none;">📄 PDF</a>
        ${selectButtonOrBadge}
      </td>
    `;
    tbody.appendChild(tr);
  });
}

function getScoreColor(score) {
  if (score >= 85) return '#34d399';
  if (score >= 60) return '#fbbf24';
  return '#f87171';
}

function renderDocumentChips(bids) {
  const container = document.getElementById('doc-chips-container');
  container.innerHTML = '';

  // Tender PDF Chip
  const tenderChip = document.createElement('a');
  tenderChip.className = 'chip';
  tenderChip.href = '/sample-pdfs/Tender_GeM_2026_Hardware.pdf';
  tenderChip.target = '_blank';
  tenderChip.innerHTML = `📘 <strong>GeM Tender Specification</strong>`;
  container.appendChild(tenderChip);

  bids.forEach(b => {
    const v = b.vendor_details;
    if (v && v.pdf_filename) {
      const chip = document.createElement('a');
      chip.className = 'chip';
      chip.href = `/sample-pdfs/${v.pdf_filename}`;
      chip.target = '_blank';
      
      let badge = '🟢';
      if (b.overall_status === 'YELLOW') badge = '🟡';
      if (b.overall_status === 'RED') badge = '🔴';

      chip.innerHTML = `${badge} ${v.vendor_name} (${v.pdf_filename})`;
      container.appendChild(chip);
    }
  });
}

function renderCartelAlerts(cartels) {
  const container = document.getElementById('cartel-alerts-container');
  container.innerHTML = '';

  if (!cartels || cartels.length === 0) {
    container.innerHTML = `
      <div class="alert-card" style="background: rgba(52,211,153,0.1); border-color: rgba(52,211,153,0.3);">
        <div class="alert-title" style="color: var(--accent-green);">✅ GNN Graph Verification Clear</div>
        <div class="alert-body">No collusive bidding rings or shared director/IP infrastructure detected across active tenders.</div>
      </div>
    `;
    return;
  }

  cartels.forEach(c => {
    const alertDiv = document.createElement('div');
    alertDiv.className = 'alert-card';
    alertDiv.innerHTML = `
      <div class="alert-title">🚨 ${c.cluster_id}: Cover Bidding & Cartel Alert</div>
      <div class="alert-body">
        <strong>Flagged Vendors:</strong> ${c.vendors.join(', ')}<br/>
        <strong>Shared Infrastructure:</strong> ${c.shared_attributes.join(', ')}<br/>
        <em>${c.description}</em>
      </div>
    `;
    container.appendChild(alertDiv);
  });
}

// D3 Force-Directed Network Graph Visualizer
function renderGNNGraph(graphData) {
  const svg = d3.select("#gnn-svg");
  svg.selectAll("*").remove();

  const width = svg.node().getBoundingClientRect().width || 500;
  const height = 450;

  const nodes = graphData.nodes.map(d => ({ ...d }));
  const links = graphData.edges.map(d => ({ ...d }));

  const simulation = d3.forceSimulation(nodes)
    .force("link", d3.forceLink(links).id(d => d.id).distance(100))
    .force("charge", d3.forceManyBody().strength(-250))
    .force("center", d3.forceCenter(width / 2, height / 2))
    .force("collision", d3.forceCollide().radius(35));

  // Render Links
  const link = svg.append("g")
    .selectAll("line")
    .data(links)
    .enter()
    .append("line")
    .attr("stroke", "#475569")
    .attr("stroke-opacity", 0.6)
    .attr("stroke-width", 1.5);

  // Render Link Labels
  const linkText = svg.append("g")
    .selectAll("text")
    .data(links)
    .enter()
    .append("text")
    .attr("font-size", "8px")
    .attr("fill", "#94a3b8")
    .attr("text-anchor", "middle")
    .text(d => d.relation);

  // Tooltip selection
  const tooltip = d3.select("#gnn-tooltip");

  // Render Nodes
  const node = svg.append("g")
    .selectAll("g")
    .data(nodes)
    .enter()
    .append("g")
    .call(d3.drag()
      .on("start", dragstarted)
      .on("drag", dragged)
      .on("end", dragended))
    .on("mouseover", function(event, d) {
      let content = `<div class="gnn-tooltip-title">${d.label}</div>`;
      content += `<div class="gnn-tooltip-row"><span class="gnn-tooltip-label">Type:</span><span class="gnn-tooltip-value" style="color: ${getNodeColor(d)}">${d.type}</span></div>`;
      
      const riskClass = d.risk_score > 75 ? 'risk-high' : (d.risk_score > 30 ? 'risk-med' : 'risk-low');
      content += `<div class="gnn-tooltip-row"><span class="gnn-tooltip-label">Risk Score:</span><span class="gnn-tooltip-value ${riskClass}">${d.risk_score}%</span></div>`;
      
      content += `<div class="gnn-tooltip-row"><span class="gnn-tooltip-label">PageRank Centrality:</span><span class="gnn-tooltip-value">${d.degree_centrality}</span></div>`;
      content += `<div class="gnn-tooltip-row"><span class="gnn-tooltip-label">Clustering Coeff:</span><span class="gnn-tooltip-value">${d.clustering_coef}</span></div>`;
      
      if (d.type === "VENDOR" && d.details) {
        content += `<div style="margin-top: 6px; padding-top: 4px; border-top: 1px dashed rgba(255,255,255,0.1);">`;
        if (d.details.gst) {
          content += `<div class="gnn-tooltip-row"><span class="gnn-tooltip-label">GSTIN:</span><span class="gnn-tooltip-value">${d.details.gst}</span></div>`;
        }
        if (d.details.pan) {
          content += `<div class="gnn-tooltip-row"><span class="gnn-tooltip-label">PAN:</span><span class="gnn-tooltip-value">${d.details.pan}</span></div>`;
        }
        if (d.details.turnover !== undefined) {
          content += `<div class="gnn-tooltip-row"><span class="gnn-tooltip-label">Turnover:</span><span class="gnn-tooltip-value">₹${d.details.turnover} L</span></div>`;
        }
        if (d.details.exp !== undefined) {
          content += `<div class="gnn-tooltip-row"><span class="gnn-tooltip-label">Experience:</span><span class="gnn-tooltip-value">${d.details.exp} Yr</span></div>`;
        }
        content += `</div>`;
      }
      
      tooltip.html(content)
        .style("opacity", 1);
    })
    .on("mousemove", function(event) {
      tooltip
        .style("left", (event.pageX + 15) + "px")
        .style("top", (event.pageY - 15) + "px");
    })
    .on("mouseleave", function() {
      tooltip.style("opacity", 0);
    });

  node.append("circle")
    .attr("r", d => d.type === "VENDOR" ? 18 : 12)
    .attr("fill", d => getNodeColor(d))
    .attr("stroke", d => d.is_suspicious ? "#f87171" : "#ffffff")
    .attr("stroke-width", d => d.is_suspicious ? 3 : 1)
    .style("filter", d => d.is_suspicious ? "drop-shadow(0 0 8px #f87171)" : "none");

  node.append("text")
    .text(d => d.label.length > 18 ? d.label.substring(0, 15) + '...' : d.label)
    .attr("x", 0)
    .attr("y", d => d.type === "VENDOR" ? 30 : 22)
    .attr("font-size", "10px")
    .attr("fill", "#e2e8f0")
    .attr("text-anchor", "middle")
    .attr("font-weight", d => d.type === "VENDOR" ? "bold" : "normal");

  simulation.on("tick", () => {
    link
      .attr("x1", d => d.source.x)
      .attr("y1", d => d.source.y)
      .attr("x2", d => d.target.x)
      .attr("y2", d => d.target.y);

    linkText
      .attr("x", d => (d.source.x + d.target.x) / 2)
      .attr("y", d => (d.source.y + d.target.y) / 2 - 4);

    node.attr("transform", d => `translate(${d.x},${d.y})`);
  });

  function dragstarted(event, d) {
    if (!event.active) simulation.alphaTarget(0.3).restart();
    d.fx = d.x;
    d.fy = d.y;
  }

  function dragged(event, d) {
    d.fx = event.x;
    d.fy = event.y;
  }

  function dragended(event, d) {
    if (!event.active) simulation.alphaTarget(0);
    d.fx = null;
    d.fy = null;
  }
}

function getNodeColor(d) {
  if (d.is_suspicious) return "#f87171"; // Red for Suspicious / Cartels
  switch (d.type) {
    case "VENDOR": return "#38bdf8";      // Cyan Vendor
    case "DIRECTOR": return "#c084fc";    // Purple Director
    case "IP_ADDRESS": return "#fbbf24";  // Yellow IP
    case "BANK_ACC": return "#34d399";    // Green Bank
    case "TENDER": return "#94a3b8";      // Slate Tender
    default: return "#64748b";
  }
}

function openAuditModal(bidId) {
  if (!currentDashboardData) return;
  const bid = currentDashboardData.bids.find(b => b.bid_id === bidId);
  if (!bid) return;

  const titleEl = document.getElementById('modal-vendor-title');
  const bodyEl = document.getElementById('modal-body-content');

  titleEl.textContent = `Audit Report: ${bid.vendor_name} (${bid.bid_id})`;

  let checksHtml = bid.itemized_checks.map(c => `
    <div style="background: rgba(255,255,255,0.03); border: 1px solid var(--border-color); padding: 0.85rem; border-radius: 8px; margin-bottom: 0.5rem;">
      <div style="display: flex; justify-content: space-between; font-weight: 600; font-size: 0.9rem; margin-bottom: 0.25rem;">
        <span>${c.check_name} <small style="color: var(--text-muted);">(${c.category})</small></span>
        <span class="status-tag ${c.status === 'PASS' ? 'green' : 'red'}">${c.status}</span>
      </div>
      <div style="font-size: 0.82rem; color: var(--text-muted);">${c.details}</div>
    </div>
  `).join('');

  bodyEl.innerHTML = `
    <div style="margin-bottom: 1rem;">
      <p><strong>Overall Score:</strong> <span style="color: ${getScoreColor(bid.overall_score)}">${bid.overall_score}%</span> | <strong>Status:</strong> ${bid.overall_status}</p>
    </div>
    <h4 style="margin-bottom: 0.5rem;">Itemized Verification Checks:</h4>
    ${checksHtml}
  `;

  document.getElementById('audit-modal').style.display = 'flex';
}

// Vendor Dashboard Helper Functions
async function handleBidUpload(file) {
  if (!file || file.type !== 'application/pdf') {
    alert('Please upload a valid PDF document.');
    return;
  }

  const progressContainer = document.getElementById('upload-progress-container');
  const progressTitle = document.getElementById('progress-status-title');
  const progressDesc = document.getElementById('progress-status-desc');
  
  progressContainer.style.display = 'flex';
  progressTitle.textContent = 'Uploading Document...';
  progressDesc.textContent = 'Uploading draft proposal file to GeM audit engine';

  const formData = new FormData();
  formData.append('file', file);

  try {
    // Stage updates for rich UX
    const stage1 = setTimeout(() => {
      progressTitle.textContent = 'Running AI Document Reader...';
      progressDesc.textContent = 'Extracting compliance and certification clauses using NLP OCR';
    }, 1200);

    const stage2 = setTimeout(() => {
      progressTitle.textContent = 'Verifying Entity Relations...';
      progressDesc.textContent = 'Running GNN collusion detection network checking shared directors / IPs';
    }, 2400);

    // Run actual upload
    const response = await fetch('/api/upload/bid', {
      method: 'POST',
      body: formData
    });

    // Clear timeout functions
    clearTimeout(stage1);
    clearTimeout(stage2);

    if (!response.ok) {
      throw new Error(`Upload failed: ${response.statusText}`);
    }

    const auditResult = await response.json();
    
    // Refresh stats
    await fetchDashboardData();

    // Store in our session list of runs
    sessionVendorBids.unshift(auditResult);

    // Switch view to report details
    renderVendorReport(auditResult);
    renderSessionHistory();

  } catch (error) {
    console.error('Error auditing bid:', error);
    alert('Failed to audit bid document. Ensure it is a valid PDF and the server is online.');
  } finally {
    progressContainer.style.display = 'none';
  }
}

function renderVendorReport(result) {
  document.getElementById('empty-report-state').style.display = 'none';
  document.getElementById('report-content-wrapper').style.display = 'block';

  // Overall Score & Color
  const score = Math.round(result.overall_score);
  const scoreColor = getScoreColor(score);
  
  document.getElementById('vendor-score-val').textContent = `${score}%`;
  document.getElementById('vendor-score-val').style.color = scoreColor;

  // Conic gradient ring
  const circle = document.querySelector('.score-circle');
  circle.style.background = `radial-gradient(closest-side, var(--bg-secondary) 79%, transparent 80% 100%), conic-gradient(${scoreColor} 0%, ${scoreColor} ${score}%, rgba(255,255,255,0.05) ${score}% 100%)`;

  // Grade Badge
  const gradeEl = document.getElementById('vendor-status-grade');
  const badgeEl = document.getElementById('vendor-overall-badge');
  const descEl = document.getElementById('vendor-status-desc');

  badgeEl.style.display = 'inline-flex';
  badgeEl.className = 'status-tag status-tag-large';
  badgeEl.classList.remove('green', 'yellow', 'red');

  if (result.overall_status === 'GREEN') {
    gradeEl.textContent = 'COMPLIANT (PASS)';
    gradeEl.style.color = 'var(--accent-green)';
    badgeEl.classList.add('green');
    badgeEl.textContent = '🟢 ELIGIBLE';
    descEl.textContent = 'Congratulations! Your bid satisfies all standard GeM clauses and compliance checks.';
  } else if (result.overall_status === 'YELLOW') {
    gradeEl.textContent = 'NEEDS REVIEW';
    gradeEl.style.color = 'var(--accent-yellow)';
    badgeEl.classList.add('yellow');
    badgeEl.textContent = '🟡 REVIEW';
    descEl.textContent = 'Your bid has minor warnings or missing data fields. Please review suggestions below.';
  } else {
    gradeEl.textContent = 'DISQUALIFIED (FAIL)';
    gradeEl.style.color = 'var(--accent-red)';
    badgeEl.classList.add('red');
    badgeEl.textContent = '🔴 DISQUALIFIED';
    descEl.textContent = 'Your bid does not satisfy mandatory eligibility rules. See corrections required below.';
  }

  // Checklist Items
  const checklistContainer = document.getElementById('vendor-itemized-checklist');
  checklistContainer.innerHTML = '';

  result.itemized_checks.forEach(check => {
    let checkBadgeClass = 'pass';
    let checkIcon = '✅';
    if (check.status === 'FAIL') {
      checkBadgeClass = 'fail';
      checkIcon = '❌';
    } else if (check.status === 'NEEDS_REVIEW' || check.status === 'REVIEW') {
      checkBadgeClass = 'review';
      checkIcon = '⚠️';
    }

    const card = document.createElement('div');
    card.className = 'checklist-item-card';
    card.innerHTML = `
      <div class="checklist-item-left">
        <div class="checklist-item-title">${checkIcon} ${check.check_name}</div>
        <div class="checklist-item-desc">${check.details}</div>
      </div>
      <span class="checklist-item-badge ${checkBadgeClass}">${check.status}</span>
    `;
    checklistContainer.appendChild(card);
  });

  // Recommendations / Suggestions Advisor
  const recContainer = document.getElementById('vendor-recommendations');
  recContainer.innerHTML = '';

  const issues = result.detected_issues || [];
  
  if (issues.length === 0 && result.overall_status === 'GREEN') {
    recContainer.innerHTML = `
      <div class="recommendation-card success">
        Your bid complies perfectly with the current specifications. No corrective action is required. You are ready to proceed with submission.
      </div>
    `;
  } else {
    // Generate helpful actions based on issues
    issues.forEach(issue => {
      const recCard = document.createElement('div');
      
      let alertClass = 'warning';
      let prefix = '⚠️ Suggestion: ';
      
      if (issue.toLowerCase().includes('fail') || issue.toLowerCase().includes('not') || issue.toLowerCase().includes('incorrect') || issue.toLowerCase().includes('expired') || issue.toLowerCase().includes('insufficient')) {
        alertClass = 'error';
        prefix = '❌ Critical Action Required: ';
      }

      recCard.className = `recommendation-card ${alertClass}`;
      
      // Map common issue strings to vendor-friendly instructions
      let friendlyText = issue;
      const lowerIssue = issue.toLowerCase();
      if (lowerIssue.includes('gst')) {
        friendlyText = `${prefix}Please make sure your organization profile or bid proposal explicitly declares a valid GSTIN starting with state code 27 (Maharashtra), 07 (Delhi), 29 (Karnataka), or 09 (Uttar Pradesh).`;
      } else if (lowerIssue.includes('turnover') || lowerIssue.includes('financial')) {
        friendlyText = `${prefix}Extracted average turnover is below the minimum threshold of ₹50.0 Lakhs. Append certified audited balance sheets for the last 3 financial years.`;
      } else if (lowerIssue.includes('iso')) {
        friendlyText = `${prefix}The ISO certification expiry date extracted is invalid or in the past. Verify that you have uploaded a valid ISO 9001:2015 certificate and that the expiry date is legible to OCR.`;
      } else if (lowerIssue.includes('experience') || lowerIssue.includes('year')) {
        friendlyText = `${prefix}The experience verification check returned less than the required 3 years. Check that all past government/enterprise purchase orders are properly appended.`;
      } else if (lowerIssue.includes('director') || lowerIssue.includes('collusion') || lowerIssue.includes('cartel') || lowerIssue.includes('ip') || lowerIssue.includes('network')) {
        friendlyText = `${prefix}Suspicious connections (shared IP address or bank account) have been flagged by the GNN network. Ensure your bid was not submitted from a shared network with other bidders.`;
      }

      recCard.textContent = friendlyText;
      recContainer.appendChild(recCard);
    });
  }
}

function renderSessionHistory() {
  const container = document.getElementById('vendor-history-list');
  container.innerHTML = '';

  if (sessionVendorBids.length === 0) {
    container.innerHTML = `<p style="color: var(--text-dim); font-size: 0.82rem; font-style: italic;">No bids uploaded in this session yet.</p>`;
    return;
  }

  sessionVendorBids.forEach((bid, index) => {
    const item = document.createElement('div');
    item.className = 'history-item';
    
    let statusBadge = '🟢';
    if (bid.overall_status === 'YELLOW') statusBadge = '🟡';
    if (bid.overall_status === 'RED') statusBadge = '🔴';

    const cleanBidId = bid.bid_id ? ` (${bid.bid_id})` : '';

    item.innerHTML = `
      <span class="history-item-name">${bid.vendor_name || 'Uploaded Bid'}${cleanBidId}</span>
      <div class="history-item-meta">
        <span class="score-pill" style="color: ${getScoreColor(bid.overall_score)}; font-size: 0.8rem;">${Math.round(bid.overall_score)}%</span>
        <span>${statusBadge}</span>
      </div>
    `;

    item.addEventListener('click', () => {
      // Toggle active styling
      document.querySelectorAll('.history-item').forEach(el => el.classList.remove('active'));
      item.classList.add('active');
      renderVendorReport(bid);
    });

    if (index === 0) {
      item.classList.add('active');
    }

    container.appendChild(item);
  });
}

async function selectBid(bidId) {
  try {
    const officer = localStorage.getItem('gem_username') || 'anonymous';
    const res = await fetch(`/api/bids/${bidId}/select?officer=${encodeURIComponent(officer)}`, { method: 'POST' });
    if (!res.ok) {
      throw new Error('Selection API error');
    }
    const data = await res.json();
    alert(data.message);
    await fetchDashboardData();
  } catch (err) {
    console.error('Error selecting bid:', err);
    alert('Failed to select bid.');
  }
}

function renderTerminalLogs(logs) {
  const container = document.getElementById('terminal-logs-container');
  if (!container) return;
  
  container.innerHTML = '';
  
  logs.forEach(log => {
    const row = document.createElement('div');
    row.className = 'terminal-row';
    
    let timeStr = '';
    try {
      const d = new Date(log.timestamp);
      timeStr = d.toTimeString().split(' ')[0];
    } catch (e) {
      timeStr = log.timestamp.split('T')[1]?.substring(0, 8) || log.timestamp;
    }
    
    const levelClass = log.level.toLowerCase();
    
    row.innerHTML = `
      <span class="term-time">[${timeStr}]</span>
      <span class="term-tag ${levelClass}">${log.level}</span>
      <span class="term-module">[${log.module}]</span>
      <span class="term-message">${log.message}</span>
    `;
    container.appendChild(row);
  });
  
  container.scrollTop = container.scrollHeight;
}

// Session Validation and Workflow Management
function checkSession() {
  const username = localStorage.getItem('gem_username');
  const role = localStorage.getItem('gem_role');
  const acknowledged = localStorage.getItem('gem_acknowledged') === 'true';

  if (!username || !role) {
    document.getElementById('auth-overlay').style.display = 'flex';
    document.getElementById('acknowledgment-overlay').style.display = 'none';
    document.getElementById('user-badge').style.display = 'none';
  } else if (!acknowledged) {
    document.getElementById('auth-overlay').style.display = 'none';
    document.getElementById('acknowledgment-overlay').style.display = 'flex';
    document.getElementById('user-badge').style.display = 'none';
  } else {
    document.getElementById('auth-overlay').style.display = 'none';
    document.getElementById('acknowledgment-overlay').style.display = 'none';
    
    const name = localStorage.getItem('gem_name') || username;
    const org = localStorage.getItem('gem_org');
    const displayStr = org ? `${name} (${org})` : name;
    document.getElementById('user-display-name').textContent = displayStr;
    document.getElementById('user-badge').style.display = 'inline-flex';
    
    applyRoleAccess(role);
    fetchDashboardData();
  }
}

function applyRoleAccess(role) {
  const tabGovt = document.getElementById('tab-govt');
  const tabVendor = document.getElementById('tab-vendor');
  const viewGovt = document.getElementById('govt-dashboard');
  const viewVendor = document.getElementById('vendor-dashboard');
  
  if (role === 'government') {
    tabGovt.style.display = 'flex';
    tabVendor.style.display = 'none';
    tabGovt.classList.add('active');
    tabVendor.classList.remove('active');
    viewGovt.classList.add('active');
    viewVendor.classList.remove('active');
    setTimeout(() => {
      if (currentDashboardData && currentDashboardData.graph_data) {
        renderGNNGraph(currentDashboardData.graph_data);
      }
    }, 100);
  } else if (role === 'vendor') {
    tabGovt.style.display = 'none';
    tabVendor.style.display = 'flex';
    tabVendor.classList.add('active');
    tabGovt.classList.remove('active');
    viewVendor.classList.add('active');
    viewGovt.classList.remove('active');
  } else {
    tabGovt.style.display = 'flex';
    tabVendor.style.display = 'flex';
  }
}

// Auth Panel Tab Switcher
window.switchAuthTab = function(mode) {
  const tabLogin = document.getElementById('tab-login');
  const tabRegister = document.getElementById('tab-register');
  const groupEmail = document.getElementById('form-group-email');
  const groupRole = document.getElementById('form-group-role');
  const groupOrg = document.getElementById('form-group-org');
  const btnSubmit = document.getElementById('btn-auth-submit');
  const errorMsg = document.getElementById('auth-error-msg');
  
  errorMsg.textContent = '';
  
  if (mode === 'login') {
    tabLogin.classList.add('active');
    tabRegister.classList.remove('active');
    groupEmail.style.display = 'none';
    groupRole.style.display = 'none';
    groupOrg.style.display = 'none';
    btnSubmit.textContent = 'Sign In';
    document.getElementById('auth-email').required = false;
    document.getElementById('auth-org').required = false;
  } else {
    tabRegister.classList.add('active');
    tabLogin.classList.remove('active');
    groupEmail.style.display = 'block';
    groupRole.style.display = 'block';
    btnSubmit.textContent = 'Register & Login';
    document.getElementById('auth-email').required = true;
    toggleOrgGroup();
  }
};

window.toggleOrgGroup = function() {
  const roleSelect = document.getElementById('auth-role');
  const groupOrg = document.getElementById('form-group-org');
  const orgInput = document.getElementById('auth-org');
  const isRegisterActive = document.getElementById('tab-register').classList.contains('active');
  
  if (isRegisterActive && roleSelect.value === 'vendor') {
    groupOrg.style.display = 'block';
    orgInput.required = true;
  } else {
    groupOrg.style.display = 'none';
    orgInput.required = false;
  }
};

window.selectAuthRole = function(role) {
  const cardVendor = document.getElementById('role-card-vendor');
  const cardGov = document.getElementById('role-card-government');
  const roleSelect = document.getElementById('auth-role');
  if (!cardVendor || !cardGov || !roleSelect) return;

  if (role === 'vendor') {
    cardVendor.classList.add('active');
    cardGov.classList.remove('active');
    roleSelect.value = 'vendor';
  } else {
    cardGov.classList.add('active');
    cardVendor.classList.remove('active');
    roleSelect.value = 'government';
  }

  // Sync Organization input display dynamically
  toggleOrgGroup();
};


// Form Auth Handler
window.handleAuthSubmit = async function(event) {
  event.preventDefault();
  
  const usernameInput = document.getElementById('auth-username');
  const passwordInput = document.getElementById('auth-password');
  const emailInput = document.getElementById('auth-email');
  const roleSelect = document.getElementById('auth-role');
  const orgInput = document.getElementById('auth-org');
  const errorMsg = document.getElementById('auth-error-msg');
  
  const isRegisterActive = document.getElementById('tab-register').classList.contains('active');
  
  errorMsg.textContent = '';
  
  try {
    if (isRegisterActive) {
      const body = {
        username: usernameInput.value.trim(),
        email: emailInput.value.trim(),
        password: passwordInput.value,
        role: roleSelect.value,
        organization: roleSelect.value === 'vendor' ? orgInput.value.trim() : null
      };
      
      const res = await fetch('/api/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      });
      
      const data = await res.json();
      if (!data.success) {
        errorMsg.textContent = data.message || 'Registration failed.';
        return;
      }
      
      localStorage.setItem('gem_username', data.username);
      localStorage.setItem('gem_role', body.role);
      localStorage.setItem('gem_name', data.name);
      if (body.organization) {
        localStorage.setItem('gem_org', body.organization);
      }
      localStorage.removeItem('gem_acknowledged');
      
    } else {
      const body = {
        username: usernameInput.value.trim(),
        password: passwordInput.value
      };
      
      const res = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      });
      
      const data = await res.json();
      if (!data.success) {
        errorMsg.textContent = data.message || 'Invalid username or password.';
        return;
      }
      
      localStorage.setItem('gem_username', data.username);
      localStorage.setItem('gem_role', data.role);
      localStorage.setItem('gem_name', data.name || data.username);
      
      // Match default seeded organizations
      let org = '';
      const u = data.username.toLowerCase();
      if (u === 'vendor') org = 'TechCorp Solutions';
      else if (u === 'infotech') org = 'InfoTech Enterprise';
      else if (u === 'globalsol') org = 'Global Digital Solutions';
      else if (u === 'alphasys') org = 'Alpha Network Systems';
      else if (u === 'betasys') org = 'Beta Systematics Pvt Ltd';
      else if (u === 'cybertech') org = 'CyberTech Innovations';
      else if (u === 'apex') org = 'Apex Hardware Traders';
      
      if (org) {
        localStorage.setItem('gem_org', org);
      }
      localStorage.removeItem('gem_acknowledged');
    }
    
    usernameInput.value = '';
    passwordInput.value = '';
    emailInput.value = '';
    orgInput.value = '';
    
    checkSession();
  } catch (err) {
    console.error('Auth error:', err);
    errorMsg.textContent = 'Server connection error. Please try again.';
  }
};

// Accept Acknowledgment Handler
window.acceptAcknowledgment = function() {
  const chk1 = document.getElementById('ack-check-1');
  const chk2 = document.getElementById('ack-check-2');
  const chk3 = document.getElementById('ack-check-3');
  
  if (!chk1.checked || !chk2.checked || !chk3.checked) {
    alert('Please acknowledge and check all statements to proceed.');
    return;
  }
  
  localStorage.setItem('gem_acknowledged', 'true');
  
  chk1.checked = false;
  chk2.checked = false;
  chk3.checked = false;
  
  checkSession();
};

// Toggle Guidance Content Accordions
window.toggleGuidance = function(contentId) {
  const content = document.getElementById(contentId);
  const arrow = document.getElementById(contentId === 'gov-guidance-content' ? 'gov-guidance-arrow' : 'vendor-guidance-arrow');
  
  if (content.style.display === 'none') {
    content.style.display = 'block';
    arrow.style.transform = 'rotate(180deg)';
  } else {
    content.style.display = 'none';
    arrow.style.transform = 'rotate(0deg)';
  }
};

// Advanced Auth Floating Inputs & Autofill Event Handlers
window.handleInputState = function(input) {
  if (input.value && input.value.trim() !== '') {
    input.setAttribute('value', input.value);
  } else {
    input.removeAttribute('value');
  }
};

window.autofillCredentials = function(username, password) {
  const userField = document.getElementById('auth-username');
  const passField = document.getElementById('auth-password');
  
  userField.value = username;
  passField.value = password;
  
  userField.setAttribute('value', username);
  passField.setAttribute('value', password);
  
  userField.dispatchEvent(new Event('input'));
  passField.dispatchEvent(new Event('input'));
  
  // Visual feedback glow animation
  userField.style.boxShadow = '0 0 12px rgba(56, 189, 248, 0.4)';
  passField.style.boxShadow = '0 0 12px rgba(56, 189, 248, 0.4)';
  userField.style.borderColor = 'var(--accent-blue)';
  passField.style.borderColor = 'var(--accent-blue)';
  
  setTimeout(() => {
    userField.style.boxShadow = '';
    passField.style.boxShadow = '';
    userField.style.borderColor = '';
    passField.style.borderColor = '';
  }, 1000);
};

window.togglePasswordVisibility = function() {
  const passField = document.getElementById('auth-password');
  const toggleBtn = document.getElementById('auth-password-toggle');
  
  if (passField.type === 'password') {
    passField.type = 'text';
    toggleBtn.textContent = '🙈';
  } else {
    passField.type = 'password';
    toggleBtn.textContent = '👁️';
  }
};

async function fetchSelectionHistory() {
  try {
    const res = await fetch('/api/selections');
    if (!res.ok) {
      throw new Error('Selections API error');
    }
    const selections = await res.json();
    currentSelections = selections;
    renderSelectionHistoryTable(selections);
  } catch (err) {
    console.error('Failed to fetch selection history:', err);
  }
}

function renderSelectionHistoryTable(selections) {
  const tbody = document.getElementById('selections-table-body');
  if (!tbody) return;
  tbody.innerHTML = '';

  if (!selections || selections.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="6" style="text-align: center; color: var(--text-dim); padding: 1.5rem; font-style: italic;">
          No procurement selections logged yet.
        </td>
      </tr>
    `;
    return;
  }

  selections.forEach((sel, index) => {
    const tr = document.createElement('tr');
    
    let timeStr = '';
    try {
      const d = new Date(sel.timestamp);
      timeStr = d.toLocaleString();
    } catch (e) {
      timeStr = sel.timestamp;
    }

    tr.innerHTML = `
      <td><span style="font-size: 0.8rem; color: var(--text-muted);">${timeStr}</span></td>
      <td><code class="font-mono">${sel.bid_id}</code></td>
      <td><strong>${sel.vendor_name}</strong></td>
      <td><code class="font-mono" style="color: var(--accent-blue);">${sel.officer_username}</code></td>
      <td><small>${sel.registered_email}</small></td>
      <td>
        <button class="email-badge" onclick="openEmailModalByIndex(${index})">
          ✉️ View Email
        </button>
      </td>
    `;
    tbody.appendChild(tr);
  });
}

window.openEmailModalByIndex = function(index) {
  const selection = currentSelections[index];
  if (!selection) return;
  const modal = document.getElementById('email-modal');
  const pre = document.getElementById('email-modal-content');
  pre.textContent = selection.email_content;
  modal.style.display = 'flex';
};

// UPGRADED FEATURE: SMART DOCUMENT CHECKLIST
window.populateBidSelectors = function(bids) {
  const selector = document.getElementById('checklist-bid-selector');
  if (!selector) return;
  
  const currentVal = selector.value;
  selector.innerHTML = '';
  
  bids.forEach(b => {
    const opt = document.createElement('option');
    opt.value = b.bid_id;
    opt.textContent = `${b.bid_id} (${b.vendor_name.substring(0, 12)}...)`;
    selector.appendChild(opt);
  });
  
  if (currentVal && bids.some(b => b.bid_id === currentVal)) {
    selector.value = currentVal;
  }
  
  loadSmartChecklist();
};

window.loadSmartChecklist = async function() {
  const selector = document.getElementById('checklist-bid-selector');
  if (!selector || !selector.value) return;
  
  const bidId = selector.value;
  const checklistContainer = document.getElementById('govt-smart-checklist-container');
  const forensicsContainer = document.getElementById('forensics-report-box');
  
  try {
    // 1. Fetch checklist overrides & status
    const res = await fetch(`/api/compliance/checklist/${bidId}`);
    const checklist = await res.json();
    
    checklistContainer.innerHTML = `
      <div style="margin-bottom:1rem; padding:0.5rem; background:rgba(255,255,255,0.02); border-radius:6px; font-size:0.8rem; border:1px solid var(--border-color);">
        <strong>Checklist Confidence Rating:</strong> 
        <span style="color:${getScoreColor(checklist.overall_confidence)}">${checklist.overall_confidence}%</span> 
        <span style="color:var(--text-dim); margin-left:0.5rem;">(Based on OCR text-layer clarity)</span>
      </div>
    `;
    
    checklist.items.forEach(item => {
      let badgeClass = 'pass';
      let icon = '✅';
      if (item.status === 'FAIL') {
        badgeClass = 'fail';
        icon = '❌';
      } else if (item.status === 'NEEDS_REVIEW') {
        badgeClass = 'review';
        icon = '⚠️';
      }
      
      const card = document.createElement('div');
      card.className = 'checklist-item-card';
      card.style.flexDirection = 'column';
      card.style.alignItems = 'stretch';
      
      card.innerHTML = `
        <div style="display:flex; justify-content:space-between; align-items:center; width:100%;">
          <div>
            <strong style="font-size:0.85rem;">${icon} ${item.name}</strong>
            <span class="badge" style="font-size:0.65rem; background:var(--bg-secondary); margin-left:0.5rem;">${item.category}</span>
          </div>
          <span class="checklist-item-badge ${badgeClass}" style="margin:0;">${item.status}</span>
        </div>
        
        <div style="margin-top:0.4rem; padding:0.4rem; background:rgba(0,0,0,0.2); border-radius:4px; font-family:var(--font-mono); font-size:0.75rem; color:var(--text-muted); word-break:break-all;">
          ${item.extracted_text}
        </div>
        
        <div class="checklist-override-actions">
          <button class="override-btn pass-btn" onclick="overrideChecklist('${bidId}', '${item.name}', 'PASS')">Verify PASS</button>
          <button class="override-btn fail-btn" onclick="overrideChecklist('${bidId}', '${item.name}', 'FAIL')">Verify FAIL</button>
        </div>
      `;
      checklistContainer.appendChild(card);
    });
    
    // 2. Fetch forensics timeline scan
    const reportRes = await fetch(`/api/analysis/risk-report/${bidId}`);
    const report = await reportRes.json();
    
    let riskBadgeClass = 'green';
    if (report.risk_rating === 'CRITICAL' || report.risk_rating === 'HIGH') {
      riskBadgeClass = 'red';
    } else if (report.risk_rating === 'MEDIUM') {
      riskBadgeClass = 'yellow';
    }
    
    // Get PDF file hash from active bids
    const activeBid = currentDashboardData.bids.find(b => b.bid_id === bidId);
    const vDetails = activeBid ? activeBid.vendor_details : {};
    
    forensicsContainer.innerHTML = `
      <div style="margin-bottom:1rem; padding:0.75rem; border:1px solid var(--border-color); border-radius:10px; background:rgba(255,255,255,0.02);">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.5rem;">
          <strong>Security Risk Rating:</strong>
          <span class="status-tag ${riskBadgeClass}">${report.risk_rating} (${report.risk_score}%)</span>
        </div>
        <div style="font-size:0.72rem; color:var(--text-dim); font-family:var(--font-mono); word-break:break-all; margin-bottom:0.25rem;">
          <strong>MD5 File Hash:</strong> ${vDetails.pdf_hash || 'unknown_hash_value'}
        </div>
        <div style="font-size:0.72rem; color:var(--text-dim); font-family:var(--font-mono);">
          <strong>PDF Producer:</strong> ${vDetails.pdf_producer || 'unknown_producer'}<br>
          <strong>PDF Created:</strong> ${vDetails.pdf_created || 'unknown_created_date'}
        </div>
      </div>
      
      <div class="forensics-item ${report.forensic_risk === 'CRITICAL' ? 'fail' : 'pass'}">
        <div class="forensics-header">
          <span>Timeline & Metadata Integrity</span>
          <span style="color:${report.forensic_risk === 'CRITICAL' ? 'var(--accent-red)' : 'var(--accent-green)'}">
            ${report.forensic_risk === 'CRITICAL' ? 'FAIL' : 'PASS'}
          </span>
        </div>
        <div class="forensics-details">
          ${report.forensic_risk === 'CRITICAL' 
            ? 'Timeline anomalies detected. ModDate registers earlier than CreationDate or template dates overlap with other vendors.'
            : 'PDF structural dates conform to standard compilation timeline logic.'}
        </div>
      </div>
      
      <div class="forensics-item ${report.network_risk === 'CRITICAL' ? 'fail' : 'pass'}">
        <div class="forensics-header">
          <span>GNN Collusion Network Scan</span>
          <span style="color:${report.network_risk === 'CRITICAL' ? 'var(--accent-red)' : 'var(--accent-green)'}">
            ${report.network_risk === 'CRITICAL' ? 'FAIL' : 'PASS'}
          </span>
        </div>
        <div class="forensics-details">
          ${report.network_risk === 'CRITICAL' 
            ? 'CRITICAL ALERT: GNN node mapping has detected overlapping director/IP relationships.'
            : 'Knowledge graph centrality verifies vendor submitted from distinct isolated infrastructure.'}
        </div>
      </div>
      
      <div style="margin-top:0.5rem; padding:0.5rem; background:rgba(37,99,235,0.04); border:1px solid rgba(37,99,235,0.2); border-radius:8px;">
        <strong style="font-size:0.8rem; color:var(--accent-blue);">AI Risk Advice:</strong>
        <ul style="padding-left:1.15rem; margin-top:0.25rem; font-size:0.75rem; color:var(--text-muted);">
          ${report.detailed_recommendations.map(r => `<li>${r}</li>`).join('')}
        </ul>
      </div>
    `;
  } catch (err) {
    console.error('Failed to load checklist or risk profile:', err);
  }
};

window.overrideChecklist = async function(bidId, itemName, status) {
  const officer = localStorage.getItem('gem_username') || 'authority_officer';
  try {
    const res = await fetch(`/api/compliance/checklist/${bidId}/verify`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ item_name: itemName, status: status, officer: officer })
    });
    if (!res.ok) throw new Error('Override response error');
    
    // Refresh stats and reload checklist panel
    await fetchDashboardData();
    loadSmartChecklist();
  } catch (err) {
    console.error('Failed to override checklist status:', err);
    alert('Failed to override checklist status.');
  }
};

// UPGRADED FEATURE: PLAGIARISM / DUPLICATE BID TRACKING
window.fetchDuplicateBids = async function() {
  const tbody = document.getElementById('duplicate-bids-table-body');
  if (!tbody) return;
  tbody.innerHTML = '';
  
  try {
    const res = await fetch('/api/fraud/duplicate-bids');
    const duplicates = await res.json();
    
    if (duplicates.length === 0) {
      tbody.innerHTML = `
        <tr>
          <td colspan="4" style="text-align: center; color: var(--text-dim); padding: 1.5rem; font-style: italic;">
            No duplicate bids or plagiarized proposals detected in this session.
          </td>
        </tr>
      `;
      return;
    }
    
    duplicates.forEach(d => {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td><strong style="color:var(--accent-red);">${d.vendor_1}</strong> <code class="font-mono">(${d.bid_id_1})</code></td>
        <td><strong style="color:var(--accent-red);">${d.vendor_2}</strong> <code class="font-mono">(${d.bid_id_2})</code></td>
        <td><span class="score-pill" style="color:var(--accent-red); font-weight:700;">${d.similarity_score}% Match</span></td>
        <td><span class="badge" style="background:rgba(220,38,38,0.15); color:var(--accent-red); font-weight:700;">${d.duplicate_type}</span></td>
      `;
      tbody.appendChild(tr);
    });
  } catch (err) {
    console.error('Failed to fetch duplicate bids list:', err);
  }
};

// UPGRADED FEATURE: AI RECOMMENDATION RANKING
window.fetchAIRecommendations = async function() {
  const tbody = document.getElementById('recommendations-table-body');
  if (!tbody) return;
  tbody.innerHTML = '';
  
  try {
    const res = await fetch('/api/recommendations/rankings');
    const rankings = await res.json();
    
    if (rankings.length === 0) {
      tbody.innerHTML = `
        <tr>
          <td colspan="6" style="text-align: center; color: var(--text-dim); padding: 1.5rem; font-style: italic;">
            No recommendation ranks available. Ensure compliant bids exist.
          </td>
        </tr>
      `;
      return;
    }
    
    rankings.forEach(r => {
      const tr = document.createElement('tr');
      
      let badgeColor = 'var(--text-dim)';
      if (r.rank === 1) badgeColor = '#fbbf24'; // Gold
      else if (r.rank === 2) badgeColor = '#cbd5e1'; // Silver
      
      const criteriaHtml = Object.entries(r.criteria_scores).map(([name, val]) => `
        <span class="criteria-pill">${name.substring(0, 10)}: <strong>${val}%</strong></span>
      `).join('');
      
      tr.innerHTML = `
        <td>
          <span style="font-size:1.4rem; font-weight:900; color:${badgeColor};">#${r.rank}</span>
        </td>
        <td>
          <strong>${r.vendor_name}</strong><br>
          <code class="font-mono" style="font-size:0.75rem;">${r.bid_id}</code>
        </td>
        <td><strong>₹${r.bid_price_lakhs} Lakhs</strong></td>
        <td>
          <div class="criteria-scores-grid">${criteriaHtml}</div>
        </td>
        <td>
          <span style="font-family:var(--font-mono); font-weight:700; color:var(--accent-blue);">${r.score}%</span>
        </td>
        <td>
          <small style="color:var(--text-muted); font-style:italic;">"${r.rationale}"</small>
        </td>
      `;
      tbody.appendChild(tr);
    });
  } catch (err) {
    console.error('Failed to load rankings leaderboard:', err);
  }
};

// UPGRADED FEATURE: DEADLINE & EXPIRY ALERT SYSTEM
window.fetchExpiryAlerts = async function() {
  const list = document.getElementById('expiry-alerts-list');
  const countBadge = document.getElementById('alert-count-badge');
  if (!list) return;
  list.innerHTML = '';
  
  try {
    const res = await fetch('/api/alerts/expiry');
    const alerts = await res.json();
    
    const criticalCount = alerts.filter(a => a.severity === 'CRITICAL').length;
    if (countBadge) {
      if (criticalCount > 0) {
        countBadge.textContent = criticalCount;
        countBadge.style.display = 'inline-block';
      } else {
        countBadge.style.display = 'none';
      }
    }
    
    if (alerts.length === 0) {
      list.innerHTML = `
        <div style="text-align: center; color: var(--text-dim); padding: 1.5rem; font-style: italic;">
          No expiration warnings or upcoming deadlines recorded.
        </div>
      `;
      return;
    }
    
    alerts.forEach(a => {
      const card = document.createElement('div');
      
      let severityClass = 'safe';
      let icon = '🔔';
      if (a.severity === 'CRITICAL') {
        severityClass = 'critical';
        icon = '🔴';
      } else if (a.severity === 'WARNING') {
        severityClass = 'warning';
        icon = '🟡';
      }
      
      card.className = `expiry-alert-card ${severityClass}`;
      card.innerHTML = `
        <div class="alert-severity-icon">${icon}</div>
        <div style="flex:1;">
          <div class="alert-info-title">${a.title} - <strong>${a.vendor_name}</strong></div>
          <div class="alert-info-desc">${a.description}</div>
          <div class="alert-meta-ticks">
            Expiry Date: ${a.expiry_date} | ${a.days_remaining < 0 ? `Expired ${Math.abs(a.days_remaining)} days ago` : `Expires in ${a.days_remaining} days`}
          </div>
        </div>
      `;
      list.appendChild(card);
    });
  } catch (err) {
    console.error('Failed to load expiry alerts:', err);
  }
};

// UPGRADED FEATURE: FLOATING AI CHATBOT CONTROLS
window.toggleChat = function() {
  const win = document.getElementById('chat-window');
  if (!win) return;
  win.style.display = win.style.display === 'none' ? 'flex' : 'none';
};

window.sendChatMessage = async function() {
  const input = document.getElementById('chat-input');
  const messagesBox = document.getElementById('chat-messages');
  if (!input || !input.value.trim()) return;
  
  const text = input.value.trim();
  input.value = '';
  
  // Append User message
  const userBubble = document.createElement('div');
  userBubble.className = 'user-msg';
  userBubble.textContent = text;
  messagesBox.appendChild(userBubble);
  messagesBox.scrollTop = messagesBox.scrollHeight;
  
  // Append Loader Bubble
  const botBubble = document.createElement('div');
  botBubble.className = 'bot-msg';
  botBubble.innerHTML = '⏳ AI is scanning documents...';
  messagesBox.appendChild(botBubble);
  messagesBox.scrollTop = messagesBox.scrollHeight;
  
  // Check active bid ID
  const selector = document.getElementById('checklist-bid-selector');
  const activeBidId = selector ? selector.value : null;
  
  try {
    const res = await fetch('/api/chatbot/query', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question: text, bid_id: activeBidId })
    });
    
    if (!res.ok) throw new Error('Chatbot response error');
    
    const reply = await res.json();
    
    // Parse Markdown elements (bullet points, bold text, lines)
    const formatted = parseMarkdownToHtml(reply.answer);
    botBubble.innerHTML = `
      ${formatted}
      <div style="font-size:0.68rem; color:var(--text-dim); border-top:1px dashed rgba(0,0,0,0.1); padding-top:0.25rem; margin-top:0.5rem; text-align:right;">
        Sources: ${reply.context_sources.join(', ')} | ${reply.timestamp.split('T')[1]?.substring(0,5) || 'Now'}
      </div>
    `;
    messagesBox.scrollTop = messagesBox.scrollHeight;
  } catch (err) {
    console.error('Chat query failed:', err);
    botBubble.textContent = '❌ Failed to connect to GeM clause audit bot. Ensure the API server is active.';
  }
};

function parseMarkdownToHtml(md) {
  let html = md;
  // Replace bold markers
  html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  html = html.replace(/__([^_]+)__/g, '<strong>$1</strong>');
  
  // Replace headings
  html = html.replace(/### ([^\n]+)/g, '<h4>$1</h4>');
  html = html.replace(/#### ([^\n]+)/g, '<h5 style="margin-top:0.35rem; font-weight:700;">$1</h5>');
  
  // Convert list bullets
  html = html.replace(/^- ([^\n]+)/gm, '<li>$1</li>');
  html = html.replace(/(<li>.*<\/li>)/gs, '<ul>$1</ul>');
  
  // Linebreaks
  html = html.replace(/\n/g, '<br>');
  return html;
}



