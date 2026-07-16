/* ========================================
   政务智能瞭望与智能问数系统 - 对话前端逻辑
   ======================================== */

(function() {
  'use strict';

  // ---- 状态 ----
  const state = {
    conversations: [],       // 对话列表 [{id, title, messages, created_at}]
    currentConvId: null,    // 当前对话ID
    messages: [],           // 当前对话消息
    models: [],             // 可用模型列表
    employees: [],          // 可用数字员工列表
    selectedModelId: null,  // 当前选中模型ID
    activeEmployee: null,   // 当前@激活的数字员工 {id, name}
    isGenerating: false,    // 是否正在生成回复
    abortController: null,  // 用于中止fetch
    convCounter: 0,         // 本地对话ID计数器
    quickMenuType: null,    // '/' 或 '@' 或 null
    welcomeHTML: '',        // 欢迎区域HTML模板
    selectedConvIds: new Set(),  // 导出选中的对话ID集合
    isExporting: false,     // 是否正在导出
    isExportMode: false,    // 是否在选择导出模式
  };

  // ---- DOM 引用 ----
  const $ = (sel) => document.querySelector(sel);
  const $$ = (sel) => document.querySelectorAll(sel);

  const els = {};
  function cacheDoms() {
    els.chatContainer = $('#chatContainer');
    els.messageList = $('#messageList');
    els.inputText = $('#inputText');
    els.sendBtn = $('#sendBtn');
    els.imgGenBtn = $('#imgGenBtn');
    els.modelSelect = $('#modelSelect');
    els.taskList = $('#taskList');
    els.sidebarTasks = $('#sidebarTasks');
    els.quickMenu = $('#quickMenu');
    els.quickMenuItems = $('#quickMenuItems');
    els.inputTag = $('#inputTag');
    els.employeeTagName = $('#employeeTagName');
    els.tagClose = $('#tagClose');
    els.stopBtn = $('#stopBtn');
    els.sidebar = $('#sidebar');
    els.sidebarOverlay = $('#sidebarOverlay');
    els.mobileToggle = $('#mobileToggle');
    els.sidebarClose = $('#sidebarClose');
    els.newChatBtn = $('#newChatBtn');
    els.clearHistoryBtn = $('#clearHistoryBtn');
    els.welcomeArea = $('#welcomeArea');
    els.exportModeBtn = $('#exportModeBtn');
    els.exportActions = $('#exportActions');
    els.exportConfirmBtn = $('#exportConfirmBtn');
    els.exportCancelBtn = $('#exportCancelBtn');
    els.selectAllCheckbox = $('#selectAllCheckbox');
  }

  // ---- 通用工具 ----
  function getCookie(name) {
    const match = document.cookie.match(new RegExp('(^| )' + name + '=([^;]+)'));
    return match ? decodeURIComponent(match[2]) : '';
  }

  // ---- 初始化 ----
  async function init() {
    cacheDoms();
    state.welcomeHTML = els.welcomeArea?.outerHTML || '';
    await loadModels();
    await loadEmployees();
    bindEvents();
    await loadConversationsFromServer();
    renderTaskList();
    // 如果没有对话，创建一个
    if (state.conversations.length === 0) {
      newConversation();
    } else {
      switchConversation(state.conversations[0].id);
    }
    // 检查是否有手势页面跳转过来的意图
    var gesturePrompt = sessionStorage.getItem('gesture_prompt');
    var gestureEmployee = sessionStorage.getItem('gesture_employee');
    if (gesturePrompt) {
      sessionStorage.removeItem('gesture_prompt');
      sessionStorage.removeItem('gesture_employee');
      els.inputText.value = gesturePrompt;
      if (gestureEmployee) {
        var emp = state.employees.find(function(e) { return e.name === gestureEmployee; });
        if (emp) {
          state.activeEmployee = { id: emp.id, name: emp.name };
          els.employeeTagName.textContent = '@' + emp.name;
          els.inputTag.style.display = 'inline-flex';
        }
      }
      setTimeout(function() { sendMessage(); }, 500);
    }
  }

  // ---- API 调用 ----
  async function loadModels() {
    try {
      const resp = await fetch('/api/user/models');
      const data = await resp.json();
      if (data.success) {
        state.models = data.data || [];
        renderModelSelect();
        // 选择默认模型
        const defaultModel = state.models.find(m => m.is_default);
        if (defaultModel) {
          state.selectedModelId = defaultModel.id;
          els.modelSelect.value = defaultModel.id;
        } else if (state.models.length > 0) {
          state.selectedModelId = state.models[0].id;
          els.modelSelect.value = state.models[0].id;
        }
      }
    } catch (e) {
      console.error('加载模型失败:', e);
    }
  }

  async function loadEmployees() {
    try {
      const resp = await fetch('/api/user/digital-employees');
      const data = await resp.json();
      if (data.success) {
        state.employees = data.data || [];
      }
    } catch (e) {
      console.error('加载数字员工失败:', e);
    }
  }

  // ---- 模型下拉 ----
  function renderModelSelect() {
    els.modelSelect.innerHTML = '';
    state.models.forEach(m => {
      const opt = document.createElement('option');
      opt.value = m.id;
      opt.textContent = m.name + (m.is_default ? ' (默认)' : '');
      els.modelSelect.appendChild(opt);
    });
  }

  // ---- 对话管理 ----
  function getXsrfUrl(url) {
    const token = getCookie('_xsrf');
    return token ? url + (url.includes('?') ? '&' : '?') + '_xsrf=' + encodeURIComponent(token) : url;
  }

  async function newConversation() {
    // 如果正在选择导出模式，先退出
    if (state.isExportMode) { exitExportMode(); }

    state.convCounter++;
    const conv = {
      id: null,
      title: '新对话',
      messages: [],
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    };
    // 先在服务器创建
    try {
      const resp = await fetch(getXsrfUrl('/api/user/conversations'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: conv.title, messages: conv.messages }),
      });
      const data = await resp.json();
      if (data.success && data.data) {
        conv.id = data.data.id;
        conv.server_id = data.data.id;
      }
    } catch (e) { console.error('创建对话失败:', e); }
    state.conversations.unshift(conv);
    switchConversation(conv.id);
    renderTaskList();
    // 聚焦输入框
    setTimeout(() => els.inputText?.focus(), 100);
  }

  function switchConversation(convId) {
    state.currentConvId = convId;
    const conv = state.conversations.find(c => c.id === convId || c.server_id === convId);
    if (!conv) return;
    state.messages = conv.messages;
    renderMessages();
    renderTaskList();
    scrollToBottom();
  }

  async function deleteConversation(convId, e) {
    e.stopPropagation();
    const conv = state.conversations.find(c => c.id === convId || c.server_id === convId);
    // 服务器删除
    if (conv && conv.server_id) {
      try {
        await fetch(getXsrfUrl('/api/user/conversations?id=' + conv.server_id), { method: 'DELETE' });
      } catch (e) { /* ignore */ }
    }
    state.conversations = state.conversations.filter(c => c.id !== convId && c.server_id !== convId);
    if (state.currentConvId === convId || state.currentConvId === conv?.server_id) {
      if (state.conversations.length > 0) {
        switchConversation(state.conversations[0].id || state.conversations[0].server_id);
      } else {
        newConversation();
      }
    }
    renderTaskList();
  }

  function clearAllHistory() {
    if (state.conversations.length === 0) return;
    if (!confirm('确定清空所有历史对话记录？')) return;
    // 逐个删除服务器上的记录
    state.conversations.forEach(c => {
      if (c.server_id) {
        fetch(getXsrfUrl('/api/user/conversations?id=' + c.server_id), { method: 'DELETE' }).catch(() => {});
      }
    });
    state.conversations = [];
    state.selectedConvIds.clear();
    newConversation();
  }

  // ========== PDF 导出相关函数 ==========

  function enterExportMode() {
    state.isExportMode = true;
    state.selectedConvIds.clear();
    els.sidebarTasks.classList.add('export-mode');
    els.exportActions.classList.add('visible');
    els.exportModeBtn.style.display = 'none';
    els.selectAllCheckbox.checked = false;
    renderTaskList();
  }

  function exitExportMode() {
    state.isExportMode = false;
    state.selectedConvIds.clear();
    els.sidebarTasks.classList.remove('export-mode');
    els.exportActions.classList.remove('visible');
    els.exportModeBtn.style.display = '';
    els.selectAllCheckbox.checked = false;
    renderTaskList();
  }

  function toggleConvSelection(convId, checked) {
    if (checked) {
      state.selectedConvIds.add(convId);
    } else {
      state.selectedConvIds.delete(convId);
    }
    updateSelectAllCheckbox();
  }

  function updateSelectAllCheckbox() {
    const total = state.conversations.length;
    const selected = state.selectedConvIds.size;
    const cb = els.selectAllCheckbox;
    if (selected === 0) {
      cb.checked = false;
      cb.indeterminate = false;
    } else if (selected === total && total > 0) {
      cb.checked = true;
      cb.indeterminate = false;
    } else {
      cb.checked = false;
      cb.indeterminate = true;
    }
  }

  function selectAllConversations(checked) {
    state.selectedConvIds.clear();
    if (checked) {
      state.conversations.forEach(c => state.selectedConvIds.add(c.id));
    }
    renderTaskList();
  }

  async function handleExportConfirm() {
    if (state.isExporting) return;
    if (state.selectedConvIds.size === 0) {
      alert('请至少选择一个对话进行导出');
      return;
    }

    // 将本地 id 转换为 server_id
    const serverIds = [];
    state.selectedConvIds.forEach(localId => {
      const conv = state.conversations.find(c => c.id === localId);
      if (conv && conv.server_id) {
        serverIds.push(conv.server_id);
      }
    });

    if (serverIds.length === 0) {
      alert('选中的对话尚未保存到服务器，请先发送消息后再导出');
      return;
    }

    await exportConversations(serverIds);
  }

  async function exportConversations(convIds) {
    state.isExporting = true;
    const confirmBtn = els.exportConfirmBtn;
    const originalText = confirmBtn.textContent;
    confirmBtn.textContent = '生成中...';
    confirmBtn.disabled = true;

    try {
      const resp = await fetch(getXsrfUrl('/api/user/export/pdf'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ conversation_ids: convIds }),
      });

      if (!resp.ok) {
        // 尝试读取错误消息
        const ct = resp.headers.get('Content-Type') || '';
        if (ct.includes('application/json')) {
          const errData = await resp.json();
          throw new Error(errData.message || `请求失败 (${resp.status})`);
        }
        throw new Error(`导出失败 (HTTP ${resp.status})`);
      }

      // 下载 PDF
      const blob = await resp.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      const disposition = resp.headers.get('Content-Disposition') || '';
      const match = disposition.match(/filename="?(.+?)"?$/);
      a.download = match ? match[1] : `chat_export_${new Date().toISOString().slice(0,10)}.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);

      // 成功后退出选择模式
      exitExportMode();
    } catch (e) {
      alert('PDF 导出失败: ' + e.message);
    } finally {
      state.isExporting = false;
      confirmBtn.textContent = originalText;
      confirmBtn.disabled = false;
    }
  }

  // ========== 原有函数继续 ==========

  function updateConvTitle(convId, title) {
    const conv = state.conversations.find(c => c.id === convId || c.server_id === convId);
    if (conv) {
      conv.title = title;
      conv.updated_at = new Date().toISOString();
      renderTaskList();
      // 服务器同步
      if (conv.server_id) {
        fetch(getXsrfUrl('/api/user/conversations'), {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ id: conv.server_id, title: title }),
        }).catch(() => {});
      }
    }
  }

  function getCurrentConv() {
    return state.conversations.find(c => c.id === state.currentConvId || c.server_id === state.currentConvId);
  }

  // ---- 服务端对话同步 ----
  async function saveMessagesToServer() {
    const conv = getCurrentConv();
    if (!conv || !conv.server_id) return;
    try {
      await fetch(getXsrfUrl('/api/user/conversations'), {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: conv.server_id, messages: state.messages }),
      });
    } catch (e) { /* ignore */ }
  }

  async function loadConversationsFromServer() {
    try {
      const resp = await fetch('/api/user/conversations');
      const data = await resp.json();
      if (data.success) {
        state.conversations = (data.data || []).map(c => ({
          id: c.id,
          server_id: c.id,
          title: c.title,
          messages: c.messages || [],
          created_at: c.created_at,
          updated_at: c.updated_at
        }));
        state.convCounter = state.conversations.length;
      }
    } catch (e) {
      console.error('加载对话失败:', e);
    }
  }

  // ---- 渲染消息 ----
  function renderMessages() {
    // 清除已有消息，但保留欢迎区域结构
    const msgElements = els.messageList.querySelectorAll('.message');
    msgElements.forEach(el => el.remove());
    // 确保欢迎区域在DOM中
    let welcomeEl = document.getElementById('welcomeArea');
    if (!welcomeEl) {
      const temp = document.createElement('div');
      temp.innerHTML = state.welcomeHTML;
      const newNode = temp.firstElementChild;
      if (newNode) {
        els.messageList.appendChild(newNode);
        els.welcomeArea = document.getElementById('welcomeArea');
      }
    }
    if (state.messages.length === 0) {
      els.welcomeArea.style.display = 'block';
      return;
    }
    els.welcomeArea.style.display = 'none';
    state.messages.forEach((msg, idx) => {
      appendMessageDOM(msg.role, msg.content, msg.employee_name, false, {
        responseFormat: msg.employee_response_format,
        extraData: msg.extra_data,
        tokens: msg.tokens,
        timeMs: msg.time_ms
      });
    });
    scrollToBottom();
  }

  function appendMessageDOM(role, content, employeeName, doScroll = true, extra = {}) {
    const div = document.createElement('div');
    div.className = `message ${role === 'user' ? 'user' : 'ai'}`;

    const avatar = document.createElement('div');
    avatar.className = 'message-avatar';
    avatar.textContent = role === 'user' ? 'U' : 'AI';

    const bubble = document.createElement('div');
    bubble.className = 'message-content';

    if (role === 'ai' && employeeName) {
      const tag = document.createElement('div');
      tag.className = 'employee-tag';
      var tagText = '🤖 ' + employeeName;
      // 显示分析意图标签
      if (extra.extraData && extra.extraData.intent) {
        var intentMap = { 'analysis': '📊 数据分析', 'chart_request': '📈 图表', 'relationship': '🔗 关系分析', 'report': '📋 报表', 'data_query': '🔍 数据查询' };
        var badge = intentMap[extra.extraData.intent];
        if (badge) tagText += ' · ' + badge;
      }
      tag.textContent = tagText;
      bubble.appendChild(tag);
    }

    // 渲染天气卡片（如适用）
    if (role === 'ai' && extra.responseFormat === 'weather_card' && extra.extraData) {
      const card = document.createElement('div');
      card.className = 'weather-card';
      const d = extra.extraData;
      card.innerHTML = `
        <div class="weather-card-header">🌤 ${d.city || '当前城市'} 天气</div>
        <div class="weather-card-body">
          <div class="weather-card-main">
            <span class="weather-card-temp">${d.temperature}°C</span>
            <span class="weather-card-desc">${d.weather}</span>
          </div>
          <div class="weather-card-details">
            <div class="weather-card-item"><span>💧 湿度</span><span>${d.humidity}%</span></div>
            <div class="weather-card-item"><span>💨 风速</span><span>${d.wind_speed} km/h ${d.wind_dir}</span></div>
            <div class="weather-card-item"><span>👁 能见度</span><span>${d.visibility} km</span></div>
            <div class="weather-card-item"><span>📊 气压</span><span>${d.pressure} hPa</span></div>
          </div>
        </div>
      `;
      bubble.appendChild(card);
    }

    // 渲染新闻卡片列表
    if (role === 'ai' && extra.responseFormat === 'news_list' && extra.extraData?.list) {
      const news = extra.extraData.list;
      const card = document.createElement('div');
      card.className = 'data-card';
      let html = '<div class="data-card-header">📰 热门新闻速递</div><div class="news-list" style="padding:4px 0;">';
      news.forEach(function(item, idx) {
        html += `
          <div style="padding:10px 12px;border-bottom:1px solid rgba(255,255,255,0.1);${idx === news.length-1 ? 'border-bottom:none;' : ''}">
            <div style="font-size:14px;font-weight:600;margin-bottom:4px;">
              <a href="${item.link}" target="_blank" style="color:#64b5f6;text-decoration:none;">${item.title}</a>
            </div>
            <div style="font-size:12px;color:rgba(255,255,255,0.65);margin-bottom:4px;">
              📍 ${item.source}  🕐 ${item.time}
            </div>
            <div style="font-size:13px;color:rgba(255,255,255,0.85);line-height:1.5;">${item.summary}</div>
          </div>`;
      });
      html += '</div>';
      card.innerHTML = html;
      bubble.appendChild(card);
    }

    // 渲染音乐播放器
    if (role === 'ai' && extra.responseFormat === 'music_player' && extra.extraData?.url) {
      const d = extra.extraData;
      const card = document.createElement('div');
      card.className = 'data-card';
      card.innerHTML = `
        <div class="data-card-header">🎵 随机音乐推荐</div>
        <div style="display:flex;align-items:center;padding:12px;">
          <img src="${d.cover || 'https://picsum.photos/seed/music/100/100'}" 
               alt="${d.song}" 
               style="width:80px;height:80px;border-radius:8px;object-fit:cover;margin-right:14px;"
               onerror="this.src='data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 width=%2280%22 height=%2280%22%3E%3Crect fill=%22%23ddd%22 width=%2280%22 height=%2280%22/%3E%3Ctext x=%2220%22 y=%2248%22 font-size=%2212%22 fill=%22%23999%22%3E🎵%3C/text%3E%3C/svg%3E'">
          <div style="flex:1;">
            <div style="font-size:16px;font-weight:600;color:#fff;">${d.song}</div>
            <div style="font-size:13px;color:rgba(255,255,255,0.7);margin:4px 0 8px;">${d.artist}</div>
            <audio controls style="width:100%;height:36px;" preload="none">
              <source src="${d.url}" type="audio/mpeg">
              您的浏览器不支持 audio 标签
            </audio>
          </div>
        </div>
      `;
      bubble.appendChild(card);
    }

    // 渲染电影详情
    if (role === 'ai' && extra.responseFormat === 'movie_detail' && extra.extraData?.title) {
      const d = extra.extraData;
      const card = document.createElement('div');
      card.className = 'data-card';
      card.innerHTML = `
        <div class="data-card-header">🎬 电影详情</div>
        <div style="display:flex;padding:12px;gap:14px;">
          <img src="${d.poster || 'https://picsum.photos/seed/movie/150/200'}" 
               alt="${d.title}" 
               style="width:120px;height:180px;border-radius:6px;object-fit:cover;flex-shrink:0;"
               onerror="this.style.display='none'">
          <div style="flex:1;">
            <div style="font-size:17px;font-weight:600;color:#fff;margin-bottom:4px;">${d.title} <span style="font-size:13px;color:rgba(255,255,255,0.5);font-weight:400;">(${d.year})</span></div>
            <div style="font-size:13px;color:#f9a825;margin-bottom:8px;">⭐ ${d.rating}</div>
            <div style="font-size:13px;color:rgba(255,255,255,0.85);margin-bottom:4px;"><b>导演：</b>${d.director}</div>
            <div style="font-size:13px;color:rgba(255,255,255,0.85);margin-bottom:8px;"><b>演员：</b>${(d.actors || []).join(' / ')}</div>
            <div style="font-size:13px;color:rgba(255,255,255,0.8);line-height:1.6;margin-bottom:10px;max-height:80px;overflow-y:auto;">${d.summary}</div>
            <a href="${d.url}" target="_blank" style="display:inline-block;padding:6px 18px;background:#e74c3c;color:#fff;border-radius:4px;text-decoration:none;font-size:13px;">查看详情</a>
          </div>
        </div>
      `;
      bubble.appendChild(card);
    }

    // 渲染数据卡片（通用卡片 - 根据card_config渲染）
    if (role === 'ai' && extra.responseFormat === 'data_card' && extra.extraData?.cardFields) {
      const cardData = extra.extraData;
      const cardConfig = extra.extraData.cardConfig || null;
      const fields = extra.extraData.cardFields || [];
      const cardTitle = extra.extraData.cardTitle || '数据卡片';
      
      const card = document.createElement('div');
      card.className = 'data-card';
      let html = `<div class="data-card-header">📋 ${cardTitle}</div>`;
      html += '<div class="data-card-body">';
      fields.forEach(function(f) {
        const label = f.label || f.key || '';
        const value = f.value !== undefined && f.value !== null ? f.value : '-';
        html += `<div class="data-card-item"><span class="data-card-label">${label}</span><span class="data-card-value">${value}</span></div>`;
      });
      html += '</div>';
      card.innerHTML = html;
      bubble.appendChild(card);
    }

    // 渲染ECharts图表（支持 line / pie / bar）
    if (role === 'ai' && extra.responseFormat === 'chart_card' && extra.extraData?.chart) {
      const chartContainer = document.createElement('div');
      chartContainer.className = 'chart-container';
      chartContainer.style.cssText = 'width:100%;height:300px;margin:10px 0;';
      bubble.appendChild(chartContainer);

      const chart = extra.extraData.chart;

      // 初始化ECharts（DOM挂载后）
      requestAnimationFrame(() => {
        if (typeof echarts !== 'undefined') {
          const myChart = echarts.init(chartContainer);
          let option = {};

          if (chart.chart_type === 'line') {
            // 折线图
            option = {
              title: { text: chart.title || '', left: 'center', textStyle: { fontSize: 14 } },
              tooltip: { trigger: 'axis' },
              legend: { data: (chart.series || []).map(function(s) { return s.name; }), bottom: 0 },
              grid: { left: '3%', right: '4%', bottom: '12%', containLabel: true },
              xAxis: { type: 'category', data: chart.x_data || [], axisLabel: { rotate: 30, fontSize: 11 } },
              yAxis: { type: 'value' },
              series: (chart.series || []).map(function(s) {
                return {
                  name: s.name, type: 'line', data: s.data,
                  smooth: true,
                  areaStyle: { opacity: 0.15 },
                  itemStyle: {
                    color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
                      { offset: 0, color: '#667eea' }, { offset: 1, color: '#22c55e' }
                    ])
                  }
                };
              })
            };
          } else if (chart.chart_type === 'pie') {
            // 饼图
            option = {
              title: { text: chart.title || '', left: 'center', textStyle: { fontSize: 14 } },
              tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
              series: [{
                name: chart.value_label || '',
                type: 'pie',
                radius: '55%',
                center: ['50%', '55%'],
                data: (chart.categories || []).map(function(name, i) {
                  return { name: name, value: (chart.values || [])[i] || 0 };
                }),
                itemStyle: { borderRadius: 4, borderColor: '#fff', borderWidth: 2 }
              }]
            };
          } else {
            // 柱状图（默认）
            option = {
              title: { text: chart.title || '', left: 'center', textStyle: { fontSize: 14 } },
              tooltip: { trigger: 'axis' },
              grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
              xAxis: { type: 'category', data: chart.categories || [], axisLabel: { rotate: 30, fontSize: 11 } },
              yAxis: { type: 'value' },
              series: [{
                name: chart.value_label || '',
                type: 'bar',
                data: (chart.values || []),
                itemStyle: {
                  color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                    { offset: 0, color: '#667eea' }, { offset: 1, color: '#764ba2' }
                  ])
                }
              }]
            };
          }
          myChart.setOption(option);
          // 窗口resize时自适应
          const resizeHandler = function() { myChart.resize(); };
          window.addEventListener('resize', resizeHandler);
          // 清理监听器
          const observer = new MutationObserver(function() {
            if (!document.contains(chartContainer)) {
              window.removeEventListener('resize', resizeHandler);
              myChart.dispose();
              observer.disconnect();
            }
          });
          observer.observe(document.body, { childList: true, subtree: true });
        }
      });
    }

    // 渲染数据表格
    if (role === 'ai' && extra.responseFormat === 'table' && extra.extraData?.table) {
      const table = extra.extraData.table;
      const columns = table.columns || [];
      const rows = table.rows || [];
      const totalRows = table.total_rows || rows.length;

      const tableWrapper = document.createElement('div');
      tableWrapper.className = 'data-table-wrapper';

      // 表头
      let html = '<div class="data-table-header">查询结果（共 ' + totalRows + ' 条记录）</div>';
      html += '<div class="table-scroll"><table class="data-result-table"><thead><tr>';
      columns.forEach(function(col) {
        html += '<th>' + col + '</th>';
      });
      html += '</tr></thead><tbody>';
      rows.forEach(function(row) {
        html += '<tr>';
        columns.forEach(function(col) {
          var val = row[col];
          html += '<td>' + (val !== null && val !== undefined ? String(val) : '') + '</td>';
        });
        html += '</tr>';
      });
      if (totalRows > rows.length) {
        html += '<tr><td colspan="' + columns.length + '" style="text-align:center;color:#94a3b8;">... 共 ' + totalRows + ' 条，仅展示前 ' + rows.length + ' 条</td></tr>';
      }
      html += '</tbody></table></div>';

      tableWrapper.innerHTML = html;
      bubble.appendChild(tableWrapper);
    }

    // 渲染Markdown（卡片类格式已自行展示内容，跳过文本避免重复）
    const cardFormats = ['weather_card', 'news_list', 'music_player', 'movie_detail', 'data_card', 'chart_card'];
    var contentDiv = null;
    if (!cardFormats.includes(extra.responseFormat)) {
      contentDiv = document.createElement('div');
      if (window.markdownit && content) {
        const md = window.markdownit({ html: true, linkify: true, breaks: true });
        contentDiv.innerHTML = md.render(content);
      } else if (content) {
        contentDiv.textContent = content;
      }
      bubble.appendChild(contentDiv);
    }

    // 添加token/响应时间信息
    if (role === 'assistant' && (extra.tokens || extra.timeMs)) {
      const meta = document.createElement('div');
      meta.className = 'message-meta';
      const parts = [];
      if (extra.timeMs) parts.push(`响应时间: ${extra.timeMs}ms`);
      if (extra.tokens !== undefined) parts.push(`token: ${extra.tokens}`);
      meta.textContent = parts.join(' · ');
      bubble.appendChild(meta);
    }

    // TTS 语音播报按钮
    if (role === 'assistant' && content) {
      const ttsBtn = document.createElement('button');
      ttsBtn.className = 'tts-btn';
      ttsBtn.title = '语音播报';
      ttsBtn.innerHTML = '🔊';
      ttsBtn.onclick = function() { toggleTTS(content, ttsBtn); };
      bubble.appendChild(ttsBtn);
    }

    div.appendChild(avatar);
    div.appendChild(bubble);

    // 添加消息到列表
    els.messageList.appendChild(div);

    if (doScroll) scrollToBottom();
    return { container: div, bubble: bubble, contentDiv: contentDiv };
  }

  function scrollToBottom() {
    setTimeout(() => {
      els.chatContainer.scrollTop = els.chatContainer.scrollHeight;
    }, 10);
  }

  // ---- 渲染任务列表 ----
  function renderTaskList() {
    els.taskList.innerHTML = '';
    state.conversations.forEach(conv => {
      const item = document.createElement('div');
      item.className = `task-item${conv.id === state.currentConvId ? ' active' : ''}`;
      item.dataset.convId = conv.id;

      // 导出复选框
      const checkbox = document.createElement('input');
      checkbox.type = 'checkbox';
      checkbox.className = 'task-checkbox';
      checkbox.dataset.convId = conv.id;
      checkbox.checked = state.selectedConvIds.has(conv.id);
      checkbox.addEventListener('click', (e) => {
        e.stopPropagation();
        toggleConvSelection(conv.id, checkbox.checked);
      });

      const icon = document.createElement('div');
      icon.className = 'task-icon';
      icon.textContent = '💬';

      const info = document.createElement('div');
      info.className = 'task-info';
      const title = document.createElement('div');
      title.className = 'task-title';
      title.textContent = conv.title || '新对话';
      const meta = document.createElement('div');
      meta.className = 'task-meta';
      const time = conv.updated_at ? new Date(conv.updated_at).toLocaleString('zh-CN') : '';
      meta.textContent = time;

      info.appendChild(title);
      info.appendChild(meta);

      const delBtn = document.createElement('button');
      delBtn.className = 'task-delete';
      delBtn.textContent = '×';
      delBtn.title = '删除对话';
      delBtn.addEventListener('click', (e) => deleteConversation(conv.id, e));

      item.appendChild(checkbox);
      item.appendChild(icon);
      item.appendChild(info);
      item.appendChild(delBtn);
      item.addEventListener('click', (e) => {
        if (e.target.tagName === 'INPUT') return;
        switchConversation(conv.id);
      });

      els.taskList.appendChild(item);
    });

    // 更新选择模式下的控件状态
    if (state.isExportMode) {
      updateSelectAllCheckbox();
    }
  }

  // ---- 发送消息 ----
  async function sendMessage() {
    const text = els.inputText.value.trim();
    if (!text || state.isGenerating) return;

    // 自动检测消息中的@员工（如建议选项点击触发）
    if (!state.activeEmployee) {
      const atMatch = text.match(/@(\S+?)(?:\s|$)/);
      if (atMatch) {
        const empName = atMatch[1];
        const emp = state.employees.find(e => e.name.includes(empName));
        if (emp) {
          state.activeEmployee = { id: emp.id, name: emp.name };
          els.employeeTagName.textContent = '@' + emp.name;
          els.inputTag.style.display = 'inline-flex';
        }
      }
    }

    // 清空输入
    els.inputText.value = '';
    autoResizeTextarea();

    // 添加用户消息
    state.messages.push({ role: 'user', content: text });
    const currentConv = getCurrentConv();
    if (currentConv) {
      // 从第一条用户消息生成标题
      if (currentConv.title === '新对话') {
        const shortTitle = text.length > 30 ? text.slice(0, 30) + '...' : text;
        updateConvTitle(currentConv.id, shortTitle);
      }
    }
    appendMessageDOM('user', text);
    await saveMessagesToServer();

    // 开始生成
    state.isGenerating = true;
    els.sendBtn.disabled = true;
    els.stopBtn.classList.add('active');

    // 创建AI消息占位
    const placeholder = appendMessageDOM('ai', '', state.activeEmployee?.name || '');
    const contentDiv = placeholder.contentDiv;
    contentDiv.classList.add('typing-cursor');

    let employeeName = state.activeEmployee?.name || '';
    let responseFormat = 'text';
    let extraData = {};
    let lastTokenCount = 0;
    let lastTimeMs = 0;

    try {
      const modelId = state.activeEmployee
        ? (state.employees.find(e => e.id === state.activeEmployee.id)?.model_id || state.selectedModelId)
        : state.selectedModelId;

      const params = new URLSearchParams();
      params.set('messages', JSON.stringify(state.messages.filter(m => m.role !== 'system')));
      if (modelId) params.set('model_id', modelId);
      if (state.activeEmployee) params.set('employee_id', state.activeEmployee.id);
      // 添加XSRF令牌防403
      const xsrfToken = getCookie('_xsrf');
      if (xsrfToken) params.set('_xsrf', xsrfToken);

      // 如果是API型数字员工，也可以通过employee_id传递
      const resp = await fetch('/api/user/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: params.toString()
      });

      if (!resp.ok) {
        throw new Error(`HTTP ${resp.status}`);
      }

      const reader = resp.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let fullContent = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed || !trimmed.startsWith('data: ')) continue;
          const dataStr = trimmed.slice(6);
          if (dataStr === '[DONE]') continue;
          try {
            const data = JSON.parse(dataStr);

            // 捕获数字员工元数据（卡片格式等）
            if (data.employee_name) {
              employeeName = data.employee_name;
            }
            if (data.employee_response_format) {
              responseFormat = data.employee_response_format;
            }
            if (data.extra_data) {
              extraData = data.extra_data;
            }
            if (data.intent) {
              if (!extraData) extraData = {};
              extraData.intent = data.intent;
            }

            // 捕获usage元数据（token数、响应时间）
            if (data.usage) {
              lastTokenCount = data.usage.completion_tokens || 0;
              lastTimeMs = data.usage.total_time_ms || 0;
              // usage数据不需要渲染为对话内容
              continue;
            }

            const delta = data?.choices?.[0]?.delta?.content || '';
            if (delta) {
              fullContent += delta;
              if (window.markdownit) {
                const md = window.markdownit({ html: true, linkify: true, breaks: true });
                contentDiv.innerHTML = md.render(fullContent);
              } else {
                contentDiv.textContent = fullContent;
              }
              scrollToBottom();
            }
          } catch (e) {
            /* skip non-JSON chunks */
          }
        }
      }

      // 完成 - 更新消息元数据（token、响应时间、卡片）
      contentDiv.classList.remove('typing-cursor');
      if (fullContent) {
        // 重建AI消息DOM，加入卡片和元数据
        const msgObj = {
          role: 'ai',
          content: fullContent,
          employee_name: employeeName,
          employee_response_format: responseFormat,
          extra_data: extraData,
          tokens: lastTokenCount,
          time_ms: lastTimeMs
        };
        state.messages.push(msgObj);
        // 替换占位消息为完整消息（含卡片和元数据）
        placeholder.container.remove();
        appendMessageDOM('ai', fullContent, employeeName, true, {
          responseFormat: responseFormat,
          extraData: extraData,
          tokens: lastTokenCount,
          timeMs: lastTimeMs
        });
        await saveMessagesToServer();
      }
    } catch (e) {
      if (e.name !== 'AbortError') {
        contentDiv.innerHTML = `<p style="color:#e74c3c">请求失败: ${e.message}</p>`;
      }
    } finally {
      state.isGenerating = false;
      els.sendBtn.disabled = false;
      els.stopBtn.classList.remove('active');
      contentDiv?.classList.remove('typing-cursor');
      // 清除@员工状态
      clearActiveEmployee();
    }
  }

  // ---- 输入框事件 ----
  function onInput(e) {
    const text = els.inputText.value;
    const cursorPos = els.inputText.selectionStart;
    const textBefore = text.slice(0, cursorPos);

    // 检测 '/' 或 '@'
    const slashIdx = textBefore.lastIndexOf('/');
    const atIdx = textBefore.lastIndexOf('@');

    // 如果输入框为空，隐藏快捷菜单
    if (!text) {
      hideQuickMenu();
      return;
    }

    if (atIdx >= 0 && atIdx > slashIdx) {
      // 检测是否在输入@查询
      const afterAt = textBefore.slice(atIdx + 1);
      // 如果没有空格或换行，表示正在输入
      if (!afterAt.includes(' ') && !afterAt.includes('\n')) {
        showAtMenu(afterAt);
        return;
      }
    }

    if (slashIdx >= 0 && slashIdx > atIdx) {
      const afterSlash = textBefore.slice(slashIdx + 1);
      if (!afterSlash.includes(' ') && !afterSlash.includes('\n')) {
        showSlashMenu(afterSlash);
        return;
      }
    }

    hideQuickMenu();
  }

  function onKeydown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
    if (e.key === 'Escape') {
      hideQuickMenu();
      clearActiveEmployee();
    }
    // 快捷菜单导航
    if (state.quickMenuType) {
      const items = $$('.quick-menu .menu-item');
      let activeIdx = -1;
      items.forEach((item, idx) => {
        if (item.classList.contains('active')) activeIdx = idx;
      });
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        const next = (activeIdx + 1) % items.length;
        items.forEach((item, idx) => item.classList.toggle('active', idx === next));
        items[next]?.scrollIntoView({ block: 'nearest' });
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        const prev = (activeIdx - 1 + items.length) % items.length;
        items.forEach((item, idx) => item.classList.toggle('active', idx === prev));
        items[prev]?.scrollIntoView({ block: 'nearest' });
      } else if (e.key === 'Enter' && activeIdx >= 0) {
        e.preventDefault();
        items[activeIdx]?.click();
      }
    }
  }

  // ---- @快捷菜单 ----
  function showAtMenu(query) {
    const items = state.employees.filter(e => {
      if (e.status === 0) return false;
      return e.name.toLowerCase().includes(query.toLowerCase());
    });
    renderQuickMenu('@ 数字员工', items.map(e => ({
      id: e.id,
      name: e.name,
      desc: e.description || (e.type === 'llm' ? 'LLM型' : 'API型'),
      icon: '🤖',
      shortcut: '',
      onClick: () => selectEmployee(e)
    })));
  }

  // ---- /快捷菜单 ----
  function showSlashMenu(query) {
    const slashItems = [
      { id: 'report', name: '生成报表', desc: '生成数据统计报表', icon: '📊', shortcut: '' },
      { id: 'chart', name: '生成图表', desc: '生成图形化数据展示', icon: '📈', shortcut: '' },
      { id: 'analyze', name: '数据分析', desc: '对已有数据进行深度分析', icon: '🔍', shortcut: '' },
      { id: 'export', name: '导出报告', desc: '导出当前对话为报告', icon: '📄', shortcut: '' },
    ];
    const filtered = slashItems.filter(item =>
      item.name.toLowerCase().includes(query.toLowerCase())
    );
    renderQuickMenu('/ 快捷功能', filtered.map(item => ({
      ...item,
      onClick: () => {
        els.inputText.value = item.name + ' ';
        els.inputText.focus();
        hideQuickMenu();
      }
    })));
  }

  function renderQuickMenu(title, items) {
    els.quickMenu.classList.add('active');
    els.quickMenuItems.innerHTML = '';
    const titleEl = document.createElement('div');
    titleEl.className = 'menu-title';
    titleEl.textContent = title;
    els.quickMenuItems.appendChild(titleEl);

    items.forEach((item, idx) => {
      const el = document.createElement('div');
      el.className = 'menu-item' + (idx === 0 ? ' active' : '');
      el.innerHTML = `
        <div class="item-icon">${item.icon}</div>
        <div>
          <div class="item-name">${item.name}</div>
          <div class="item-desc">${item.desc}</div>
        </div>
        ${item.shortcut ? `<div class="item-shortcut">${item.shortcut}</div>` : ''}
      `;
      el.addEventListener('click', item.onClick);
      els.quickMenuItems.appendChild(el);
    });
    state.quickMenuType = title.startsWith('@') ? '@' : '/';
  }

  function hideQuickMenu() {
    els.quickMenu.classList.remove('active');
    state.quickMenuType = null;
  }

  // ---- @数字员工选择 ----
  function selectEmployee(emp) {
    state.activeEmployee = { id: emp.id, name: emp.name };
    els.employeeTagName.textContent = '@' + emp.name;
    els.inputTag.style.display = 'inline-flex';
    hideQuickMenu();

    // 移除输入中的@文本
    const text = els.inputText.value;
    const cursorPos = els.inputText.selectionStart;
    const before = text.slice(0, cursorPos);
    const after = text.slice(cursorPos);
    const atIdx = before.lastIndexOf('@');
    const newBefore = before.slice(0, atIdx);
    els.inputText.value = newBefore + after;
    els.inputText.focus();
  }

  function clearActiveEmployee() {
    state.activeEmployee = null;
    els.inputTag.style.display = 'none';
  }

  // ---- 自动调整输入框高度 ----
  function autoResizeTextarea() {
    els.inputText.style.height = 'auto';
    els.inputText.style.height = Math.min(els.inputText.scrollHeight, 160) + 'px';
  }

  // ---- 事件绑定 ----
  function bindEvents() {
    // 发送
    els.sendBtn.addEventListener('click', sendMessage);
    // 生图
    els.imgGenBtn.addEventListener('click', imageGen);
    els.inputText.addEventListener('input', (e) => {
      onInput(e);
      autoResizeTextarea();
    });
    els.inputText.addEventListener('keydown', onKeydown);

    // 停止生成
    els.stopBtn.addEventListener('click', () => {
      // 不支持中止fetch流，刷新状态
      state.isGenerating = false;
      els.sendBtn.disabled = false;
      els.stopBtn.classList.remove('active');
    });

    // 模型切换
    els.modelSelect.addEventListener('change', () => {
      state.selectedModelId = parseInt(els.modelSelect.value);
    });

    // 新对话
    els.newChatBtn.addEventListener('click', newConversation);

    // 清空历史
    els.clearHistoryBtn.addEventListener('click', clearAllHistory);

    // PDF 导出
    els.exportModeBtn?.addEventListener('click', enterExportMode);
    els.exportConfirmBtn?.addEventListener('click', handleExportConfirm);
    els.exportCancelBtn?.addEventListener('click', exitExportMode);
    els.selectAllCheckbox?.addEventListener('change', () => {
      selectAllConversations(els.selectAllCheckbox.checked);
    });

    // @标签关闭
    els.tagClose.addEventListener('click', clearActiveEmployee);

    // 侧栏移动端切换
    els.mobileToggle?.addEventListener('click', () => {
      els.sidebar.classList.add('open');
      els.sidebarOverlay.classList.add('active');
    });
    els.sidebarClose?.addEventListener('click', () => {
      els.sidebar.classList.remove('open');
      els.sidebarOverlay.classList.remove('active');
    });
    els.sidebarOverlay?.addEventListener('click', () => {
      els.sidebar.classList.remove('open');
      els.sidebarOverlay.classList.remove('active');
    });
    // 点击右侧对话区关闭左侧侧栏（移动端）
    els.chatContainer?.addEventListener('click', () => {
      if (window.innerWidth <= 768 && els.sidebar.classList.contains('open')) {
        els.sidebar.classList.remove('open');
        els.sidebarOverlay.classList.remove('active');
      }
    });

    // 点击页面其他区域关闭快捷菜单
    document.addEventListener('click', (e) => {
      if (!e.target.closest('.input-container')) {
        hideQuickMenu();
      }
    });
  }

  // ---- 图片生成 ----
  async function imageGen() {
    const prompt = els.inputText.value.trim();
    if (!prompt) return;
    if (state.isGenerating) return;
    state.isGenerating = true;
    els.sendBtn.disabled = true;
    els.imgGenBtn.disabled = true;

    appendMessageDOM('user', '🎨 生成图片: ' + prompt);
    els.inputText.value = '';

    const placeholder = appendMessageDOM('assistant', '🎨 正在生成图片...');

    try {
      const formData = new URLSearchParams();
      formData.append('prompt', prompt);
      formData.append('_xsrf', getCookie('_xsrf'));
      const resp = await fetch(getXsrfUrl('/api/user/image-gen'), {
        method: 'POST',
        body: formData,
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
      });
      const data = await resp.json();

      placeholder.container.remove();
      if (data.ok && data.image_url) {
        const imgDiv = appendMessageDOM('assistant', '', '图片生成', true);
        const img = document.createElement('img');
        img.src = data.image_url;
        img.style.cssText = 'max-width:100%;border-radius:12px;margin-top:8px;';
        img.onerror = function() { img.alt = '图片加载失败，URL: ' + data.image_url; };
        imgDiv.bubble.appendChild(img);
      } else {
        appendMessageDOM('assistant', '❌ ' + (data.msg || '生成失败'));
      }
    } catch (e) {
      placeholder.container.remove();
      appendMessageDOM('assistant', '❌ 请求失败: ' + e.message);
    } finally {
      state.isGenerating = false;
      els.sendBtn.disabled = false;
      els.imgGenBtn.disabled = false;
    }
  }

  // ---- TTS 语音播报 ----
  let ttsUtterance = null;

  function toggleTTS(text, btn) {
    if (ttsUtterance && window.speechSynthesis.speaking) {
      window.speechSynthesis.cancel();
      btn.innerHTML = '🔊';
      return;
    }
    const cleanText = text.replace(/<[^>]*>/g, '').replace(/[*#_`~>\[\]]/g, '').trim();
    if (!cleanText) return;
    ttsUtterance = new SpeechSynthesisUtterance(cleanText);
    ttsUtterance.lang = 'zh-CN';
    ttsUtterance.rate = 1.0;
    ttsUtterance.onstart = function() { btn.innerHTML = '🔇'; };
    ttsUtterance.onend = function() { btn.innerHTML = '🔊'; ttsUtterance = null; };
    ttsUtterance.onerror = function() { btn.innerHTML = '🔊'; ttsUtterance = null; };
    window.speechSynthesis.speak(ttsUtterance);
  }

  // ---- 启动 ----
  document.addEventListener('DOMContentLoaded', init);
})();
