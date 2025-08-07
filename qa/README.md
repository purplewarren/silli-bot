# Silli Dyad QA Manual Testing Guide

This guide provides step-by-step manual testing procedures for the Silli Dyad features (Tantrum Translator and Meal Mood Companion).

## Prerequisites

- ✅ Bot running on `localhost:8000` (or configured port)
- ✅ PWA running on `http://localhost:5173/silli-meter/`
- ✅ Valid JWT token for testing
- ✅ Test video file (20-40s with audible speech)
- ✅ Test meal photo (clear plate image)

## Test Environment Setup

1. **Start Bot**: Ensure the Silli bot is running and accessible
2. **Start PWA**: Ensure the Vite dev server is running
3. **Clear Storage**: Clear browser localStorage/IndexedDB for clean testing
4. **Network**: Ensure no network calls to third parties during analysis

---

## 1. Tantrum Translator Testing

### 1.1 Basic Flow Test

**URL**: `http://localhost:5173/silli-meter/?dyad=tantrum`

**Steps**:
1. ✅ **Home Screen**: Verify tantrum home loads with intensity slider (1-10)
2. ✅ **Action Buttons**: Verify [🎤 Upload Voice], [🎥 Upload Video], [📝 Add Text] buttons
3. ✅ **Privacy Notice**: Verify "Your recordings never leave your device" is displayed

### 1.2 Video Upload Test

**Steps**:
1. ✅ **Upload Video**: Click [🎥 Upload Video] and select 20-40s test video
2. ✅ **Processing**: Verify video uploads and processing begins
3. ✅ **Analysis**: Verify motion score computation (should show progress)
4. ✅ **Thermometer**: Verify escalation index appears and thermometer updates
5. ✅ **Tip Display**: Verify context-aware tip appears based on trigger/escalation
6. ✅ **Badge Check**: Verify appropriate badge appears (if conditions met)

**Expected Results**:
- Video processes without network calls
- Escalation index calculated (0.00-1.00 range)
- Thermometer visual updates
- Tip appears relevant to trigger/escalation level
- Badge appears for positive actions

### 1.3 Process & Relay Test

**Steps**:
1. ✅ **Process Results**: Click "Process Results" button
2. ✅ **Export**: Verify JSON export downloads with correct schema
3. ✅ **Relay**: Verify data posts to bot `/ingest` endpoint
4. ✅ **Bot Response**: Verify bot confirms within 15 seconds
5. ✅ **Status**: Verify relay returns HTTP 200

**Expected Results**:
- JSON export contains `metrics.escalation_index`
- JSON export contains `media_summaries.video.motion_score_p95`
- Bot responds with confirmation
- No network calls to third parties

### 1.4 List Display Test

**Steps**:
1. ✅ **Navigate to List**: Go to bot and run `/list` command
2. ✅ **Tantrum Entry**: Verify entry shows `dyad:tantrum · esc=0.XX`
3. ✅ **Format Check**: Verify escalation index appears in correct format
4. ✅ **Data Accuracy**: Verify escalation value matches exported data

**Expected Results**:
- List shows `dyad:tantrum · esc=0.65` (example)
- Escalation index matches exported value
- Entry appears in chronological order

### 1.5 History & Delete Test

**Steps**:
1. ✅ **History Screen**: Navigate to tantrum history
2. ✅ **Session Display**: Verify session appears with `· esc=0.XX` format
3. ✅ **Insights**: Verify insights show average escalation, common trigger, noise %
4. ✅ **Delete Single**: Click delete button on individual session
5. ✅ **Delete All**: Click "Clear All" button
6. ✅ **Storage Check**: Verify only tantrum data is cleared

**Expected Results**:
- History shows session with escalation index in date line
- Insights display 2-3 concise lines with averages
- Individual delete removes only that session
- Clear All removes only tantrum data (preserves other dyads)

---

## 2. Meal Mood Companion Testing

### 2.1 Basic Flow Test

**URL**: `http://localhost:5173/silli-meter/?dyad=meal`

**Steps**:
1. ✅ **Home Screen**: Verify meal home loads with star rating (1-5)
2. ✅ **Action Buttons**: Verify [📷 Snap Meal], [🎤 Ask a question] buttons
3. ✅ **Privacy Notice**: Verify "Your photos are analyzed on your device" is displayed

### 2.2 Photo Capture Test

**Steps**:
1. ✅ **Take Photo**: Click [📷 Snap Meal] and capture plate photo
2. ✅ **Processing**: Verify photo uploads and analysis begins
3. ✅ **Image Analysis**: Verify dietary diversity, clutter score, plate coverage computed
4. ✅ **Mood Calculation**: Verify meal mood calculated and displayed
5. ✅ **Tip Display**: Verify context-aware tip appears
6. ✅ **Badge Check**: Verify appropriate badge appears (if conditions met)

**Expected Results**:
- Photo processes without network calls
- Image heuristics calculated (diversity, clutter, coverage)
- Meal mood calculated (0-100 range)
- Tip appears relevant to image analysis
- Badge appears for positive characteristics

### 2.3 Context Form Test

**Steps**:
1. ✅ **Form Fields**: Set eaten_pct=40, stress_level=2
2. ✅ **Mood Adjustment**: Verify meal mood adjusts based on context
3. ✅ **Tip Update**: Verify tip changes based on new context
4. ✅ **Validation**: Verify form validation works correctly

**Expected Results**:
- Meal mood adjusts: `meal_mood_adj = clamp(meal_mood + 10*(diversity-0.5) - 10*(clutter-0.5), 0, 100)`
- Tip selection considers stress level and eaten percentage
- Form saves context data correctly

### 2.4 Process & Relay Test

**Steps**:
1. ✅ **Process Results**: Click "Process Results" button
2. ✅ **Export**: Verify JSON export downloads with correct schema
3. ✅ **Relay**: Verify data posts to bot `/ingest` endpoint
4. ✅ **Bot Response**: Verify bot confirms within 15 seconds
5. ✅ **Status**: Verify relay returns HTTP 200

**Expected Results**:
- JSON export contains `metrics.meal_mood`
- JSON export contains `media_summaries.image` with heuristics
- Bot responds with confirmation
- No network calls to third parties

### 2.5 List Display Test

**Steps**:
1. ✅ **Navigate to List**: Go to bot and run `/list` command
2. ✅ **Meal Entry**: Verify entry shows `dyad:meal · mood=XX`
3. ✅ **Format Check**: Verify meal mood appears in correct format
4. ✅ **Data Accuracy**: Verify mood value matches exported data

**Expected Results**:
- List shows `dyad:meal · mood=75` (example)
- Meal mood matches exported value
- Entry appears in chronological order

### 2.6 Gallery & Delete Test

**Steps**:
1. ✅ **Gallery Screen**: Navigate to meal gallery
2. ✅ **Thumbnail Display**: Verify meal appears with thumbnail
3. ✅ **Mood Display**: Verify session shows `· mood=XX` format
4. ✅ **Insights**: Verify insights show average mood, eaten %, diversity
5. ✅ **Delete Single**: Click delete button on individual meal
6. ✅ **Delete All**: Click "Clear All" button
7. ✅ **Storage Check**: Verify only meal data is cleared

**Expected Results**:
- Gallery shows meal with thumbnail and mood in date line
- Insights display 2-3 concise lines with averages
- Individual delete removes only that meal
- Clear All removes only meal data (preserves other dyads)

---

## 3. Insights Testing

### 3.1 Tantrum Insights

**Steps**:
1. ✅ **Navigate to History**: Go to tantrum history screen
2. ✅ **Insights Section**: Verify insights section appears
3. ✅ **Average Escalation**: Verify average escalation index displayed
4. ✅ **Common Trigger**: Verify most frequent trigger identified
5. ✅ **Environment Noise**: Verify percentage of sessions with noise

**Expected Results**:
- Insights show 2-3 concise lines
- Average escalation: "Your average escalation index is 0.45"
- Common trigger: "Most frequent trigger: transition"
- Environment noise: "Audio noise: 85.7%, Video noise: 42.9%"

### 3.2 Meal Insights

**Steps**:
1. ✅ **Navigate to Gallery**: Go to meal gallery screen
2. ✅ **Insights Section**: Verify insights section appears
3. ✅ **Average Mood**: Verify average meal mood displayed
4. ✅ **Eaten Percentage**: Verify average eaten percentage (if available)
5. ✅ **Dietary Diversity**: Verify average dietary diversity

**Expected Results**:
- Insights show 2-3 concise lines
- Average mood: "Your average meal mood is 72/100"
- Eaten percentage: "Your child eats 65% of meals on average"
- Dietary diversity: "Your average dietary diversity is 68%"

---

## 4. Automated Testing

### 4.1 Run QA Script

**Steps**:
1. ✅ **Install Dependencies**: `pip install requests`
2. ✅ **Configure Script**: Update URLs and JWT token in `qa/push_samples.py`
3. ✅ **Run Tests**: `python qa/push_samples.py`
4. ✅ **Verify Results**: Check all sessions post successfully

**Expected Results**:
- All tantrum sessions post to bot/worker
- All meal sessions post to bot/worker
- Bot confirms each session within 15 seconds
- No network errors or timeouts

### 4.2 Schema Validation

**Steps**:
1. ✅ **Load Samples**: Script loads `fake_tantrum_sessions.json` and `fake_meal_sessions.json`
2. ✅ **Validate Schema**: Each session validated against expected schema
3. ✅ **Check Fields**: Required fields present and dyad-specific fields correct

**Expected Results**:
- All sessions pass schema validation
- Required fields: version, family_id, session_id, mode, dyad, etc.
- Tantrum sessions have `metrics.escalation_index`
- Meal sessions have `metrics.meal_mood`

---

## 5. Edge Cases & Error Handling

### 5.1 Network Disconnection

**Steps**:
1. ✅ **Disconnect Network**: Turn off internet connection
2. ✅ **Try Analysis**: Attempt video/photo analysis
3. ✅ **Verify Local**: Confirm all analysis happens on-device
4. ✅ **Check Export**: Verify export still works locally

**Expected Results**:
- Analysis completes without network calls
- Export generates JSON file locally
- No errors due to network unavailability

### 5.2 Invalid Input

**Steps**:
1. ✅ **Invalid Video**: Try uploading non-video file
2. ✅ **Invalid Photo**: Try uploading non-image file
3. ✅ **Empty Form**: Submit form without required fields
4. ✅ **Large Files**: Try uploading very large files

**Expected Results**:
- Appropriate error messages displayed
- No crashes or undefined behavior
- Graceful handling of invalid inputs

### 5.3 Storage Limits

**Steps**:
1. ✅ **Add Many Sessions**: Create 30+ sessions
2. ✅ **Check Storage**: Verify automatic localStorage → IndexedDB switch
3. ✅ **Performance**: Verify app remains responsive
4. ✅ **Data Integrity**: Verify all data preserved

**Expected Results**:
- Automatic storage optimization
- No performance degradation
- All data preserved correctly

---

## 6. Acceptance Criteria Verification

### 6.1 Privacy-First ✅
- [ ] All analysis happens on-device
- [ ] No network calls during analysis
- [ ] PII flag always set to false
- [ ] Clear privacy notices displayed

### 6.2 Relay Path ✅
- [ ] Export generates valid JSON
- [ ] Bot receives data via /ingest
- [ ] Bot confirms within 15 seconds
- [ ] /list shows dyad-specific metrics

### 6.3 Data Integrity ✅
- [ ] Tantrum: escalation_index in metrics
- [ ] Meal: meal_mood in metrics
- [ ] Media summaries include analysis results
- [ ] Context data preserved correctly

### 6.4 User Experience ✅
- [ ] Clean, intuitive interface
- [ ] Responsive design
- [ ] Clear feedback and progress indicators
- [ ] Consistent navigation patterns

---

## Troubleshooting

### Common Issues

1. **Bot Not Responding**
   - Check bot is running on correct port
   - Verify JWT token is valid
   - Check bot logs for errors

2. **Analysis Fails**
   - Verify file format is supported
   - Check browser console for errors
   - Ensure sufficient device memory

3. **Storage Issues**
   - Clear browser storage
   - Check IndexedDB support
   - Verify storage permissions

4. **Network Errors**
   - Check internet connection
   - Verify bot/worker URLs
   - Check firewall settings

### Debug Commands

```bash
# Check bot status
curl http://localhost:8000/health

# Test JWT token
curl -H "Authorization: Bearer YOUR_TOKEN" http://localhost:8000/ingest

# Check PWA status
curl http://localhost:5173/silli-meter/

# Run automated tests
python qa/push_samples.py
```

---

## 7. Reasoner Smoke Test

### 7.1 Prerequisites

Before running the reasoner smoke test, ensure:

1. **Ollama is running** with the required model:
   ```bash
   # Start Ollama
   ollama serve
   
   # Ensure model is present (e.g., llama3.2:3b)
   ollama list
   ```

2. **Reasoner service is running**:
   ```bash
   # Start the reasoner
   python reasoner/app.py
   ```

3. **Bot is configured** with reasoner enabled:
   ```bash
   # Set environment variable
   export REASONER_ENABLED=1
   
   # Restart the bot
   python -m bot.main
   ```

### 7.2 Running the Smoke Test

**Step-by-step instructions**:

1. **Start Ollama**:
   ```bash
   ollama serve
   ```

2. **Ensure model is present**:
   ```bash
   ollama list
   # Should show your configured model (e.g., llama3.2:3b)
   ```

3. **Start reasoner service**:
   ```bash
   python reasoner/app.py
   # Should start on http://localhost:5001
   ```

4. **Configure bot for reasoner**:
   ```bash
   # Set environment variables
   export REASONER_ENABLED=1
   export REASONER_BASE_URL=http://localhost:5001
   
   # Restart bot
   python -m bot.main
   ```

5. **Run smoke test**:
   ```bash
   python qa/reasoner_smoke.py
   ```

### 7.3 Expected Results

**When reasoner is enabled** (`REASONER_ENABLED=1`):
- ✅ Session ingestion succeeds
- ✅ Reasoner usage appears in logs: `reasoner_used=yes`
- ✅ Latency metrics captured: `latency_ms=XXX`
- ✅ Tips appear in bot responses: `"Suggested next step"`
- ✅ Overall test result: `✅ PASS`

**When reasoner is disabled** (`REASONER_ENABLED=0`):
- ✅ Session ingestion succeeds
- ✅ Reasoner usage logs: `reasoner_used=no (disabled)`
- ✅ No tips in bot responses
- ✅ Overall test result: `❌ FAIL` (expected, since no tips)

### 7.4 Troubleshooting

**Common issues**:

1. **Ollama not running**:
   ```bash
   # Start Ollama
   ollama serve
   ```

2. **Model not found**:
   ```bash
   # Pull the required model
   ollama pull llama3.2:3b
   ```

3. **Reasoner service not responding**:
   ```bash
   # Check reasoner is running
   curl http://localhost:5001/health
   
   # Check reasoner logs
   tail -f logs/reasoner.log
   ```

4. **Bot not configured**:
   ```bash
   # Verify environment variables
   echo $REASONER_ENABLED
   echo $REASONER_BASE_URL
   
   # Restart bot with correct config
   REASONER_ENABLED=1 REASONER_BASE_URL=http://localhost:5001 python -m bot.main
   ```

5. **No tips appearing**:
   - Check bot logs for `reasoner_used=yes`
   - Verify reasoner is returning tips in response
   - Check bot logs for `"Suggested next step"`

### 7.5 Test Output Example

```
🚀 Starting Reasoner Smoke Test
==================================================

🧪 Test 1: Tantrum Session
------------------------------
✅ Session ingested successfully: smoke_tantrum_1703123456
⏳ Waiting for bot to process ingested data...
✅ Found reasoner usage in logs: reasoner_used=yes dyad=tantrum latency_ms=1250
📊 Reasoner latency: 1250ms
✅ Found tips in bot response: Suggested next step: Try offering a 5-minute warning before transitions

🧪 Test 2: Meal Session
------------------------------
✅ Session ingested successfully: smoke_meal_1703123457
⏳ Waiting for bot to process ingested data...
✅ Found reasoner usage in logs: reasoner_used=yes dyad=meal latency_ms=980
📊 Reasoner latency: 980ms
✅ Found tips in bot response: Suggested next step: Consider offering smaller portions to reduce pressure

📊 Test Summary
==================================================
Tantrum: ✅ PASS (latency: 1250ms)
Meal: ✅ PASS (latency: 980ms)

🎯 Overall Result: ✅ PASS
```

---

## Test Completion Checklist

- [ ] Tantrum video upload and analysis works
- [ ] Meal photo capture and analysis works
- [ ] Both dyads export valid JSON
- [ ] Bot receives and confirms all sessions
- [ ] /list shows dyad-specific metrics
- [ ] History/gallery displays insights correctly
- [ ] Delete functions work properly
- [ ] No network calls during analysis
- [ ] All acceptance criteria met
- [ ] Automated tests pass

**Status**: 🟡 In Progress / 🟢 Complete / 🔴 Failed 