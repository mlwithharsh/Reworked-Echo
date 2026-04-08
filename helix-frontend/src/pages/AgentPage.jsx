import React, { startTransition, useEffect, useMemo, useState } from 'react';
import { motion } from 'framer-motion';
import toast from 'react-hot-toast';
import {
  Activity,
  Bot,
  Brain,
  CalendarClock,
  CheckCircle2,
  ChevronRight,
  Clock3,
  FileText,
  LineChart,
  Radio,
  RefreshCw,
  Send,
  ShieldCheck,
  Sparkles,
} from 'lucide-react';
import { marketingAPI } from '../api/client';

const defaultBrandForm = {
  brand_name: '',
  voice_style: '',
  preferred_vocabulary: '',
  banned_phrases: '',
  signature_patterns: '',
  default_cta_style: '',
  audience_notes: '',
  positioning: '',
};

const defaultCampaignForm = {
  name: '',
  goal: '',
  target_audience: '',
  offer_summary: '',
  brand_profile_id: '',
  brand_voice: '',
};

const defaultGenerationForm = {
  platforms: 'linkedin,x,telegram',
  experiment_labels: 'A,B',
  desired_tone: '',
  cta_style: '',
  extra_context: '',
};

const defaultPerformanceForm = {
  platform: 'linkedin',
  metric_type: 'click_rate',
  metric_value: '',
  note: '',
};

const platformEnvHints = {
  discord: ['HELIX_DISCORD_WEBHOOK_URL', 'or HELIX_DISCORD_BOT_TOKEN + HELIX_DISCORD_CHANNEL_ID'],
  linkedin: ['HELIX_LINKEDIN_ACCESS_TOKEN', 'HELIX_LINKEDIN_AUTHOR_URN'],
  reddit: [
    'HELIX_REDDIT_CLIENT_ID',
    'HELIX_REDDIT_CLIENT_SECRET',
    'HELIX_REDDIT_USERNAME',
    'HELIX_REDDIT_PASSWORD',
    'HELIX_REDDIT_SUBREDDIT',
  ],
  telegram: ['HELIX_TELEGRAM_BOT_TOKEN', 'HELIX_TELEGRAM_CHAT_ID'],
  webhook: ['HELIX_MARKETING_WEBHOOK_URL'],
  x: ['HELIX_X_ACCESS_TOKEN'],
};

const platformCredentialFields = {
  discord: ['discord_webhook_url', 'discord_bot_token', 'discord_channel_id'],
  linkedin: ['linkedin_access_token', 'linkedin_author_urn'],
  reddit: ['reddit_client_id', 'reddit_client_secret', 'reddit_username', 'reddit_password', 'reddit_default_subreddit'],
  telegram: ['telegram_bot_token', 'telegram_chat_id'],
  webhook: ['marketing_webhook_url'],
  x: ['x_access_token'],
};

const AgentPage = () => {
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [workspaceNotice, setWorkspaceNotice] = useState('');
  const [brands, setBrands] = useState([]);
  const [campaigns, setCampaigns] = useState([]);
  const [variants, setVariants] = useState([]);
  const [schedules, setSchedules] = useState([]);
  const [logs, setLogs] = useState([]);
  const [platformHealth, setPlatformHealth] = useState([]);
  const [channelCredentials, setChannelCredentials] = useState([]);
  const [analytics, setAnalytics] = useState(null);
  const [optimization, setOptimization] = useState(null);
  const [strategy, setStrategy] = useState(null);
  const [scheduleFilter, setScheduleFilter] = useState('all');
  const [logFilter, setLogFilter] = useState('all');
  const [brandForm, setBrandForm] = useState(defaultBrandForm);
  const [campaignForm, setCampaignForm] = useState(defaultCampaignForm);
  const [generationForm, setGenerationForm] = useState(defaultGenerationForm);
  const [performanceForm, setPerformanceForm] = useState(defaultPerformanceForm);
  const [selectedBrandId, setSelectedBrandId] = useState('');
  const [selectedCampaignId, setSelectedCampaignId] = useState('');
  const [selectedVariantIds, setSelectedVariantIds] = useState([]);
  const [credentialPlatform, setCredentialPlatform] = useState('x');
  const [credentialAccountLabel, setCredentialAccountLabel] = useState('default');
  const [credentialValues, setCredentialValues] = useState({});
  const [scheduleAt, setScheduleAt] = useState(() => {
    const next = new Date(Date.now() + 60 * 60 * 1000);
    return next.toISOString().slice(0, 16);
  });

  const selectedCampaign = useMemo(
    () => campaigns.find((campaign) => campaign.id === selectedCampaignId) || null,
    [campaigns, selectedCampaignId],
  );

  const approvedVariants = useMemo(
    () => variants.filter((variant) => variant.approval_status === 'approved'),
    [variants],
  );

  const platformHealthMap = useMemo(
    () => Object.fromEntries(platformHealth.map((item) => [item.platform, item])),
    [platformHealth],
  );

  const summaryCards = useMemo(() => {
    const queuedJobs = schedules.filter((job) => ['pending', 'queued', 'running'].includes(job.status)).length;
    const readyPlatforms = platformHealth.filter((item) => item.configured).length;
    return [
      { label: 'Campaigns', value: campaigns.length, icon: Bot, tone: 'from-[#7f9476]/18 to-[#bfa98b]/10' },
      { label: 'Approved Variants', value: approvedVariants.length, icon: CheckCircle2, tone: 'from-[#bfa98b]/18 to-[#7f9476]/10' },
      { label: 'Queued Jobs', value: queuedJobs, icon: CalendarClock, tone: 'from-[#d8cfbf] to-[#bfa98b]/12' },
      { label: 'Live-Ready Platforms', value: readyPlatforms, icon: LineChart, tone: 'from-[#7f9476]/10 to-[#d8cfbf]' },
    ];
  }, [approvedVariants.length, campaigns.length, platformHealth, schedules]);

  const selectedVariantWarnings = useMemo(() => {
    return selectedVariantIds
      .map((variantId) => variants.find((item) => item.id === variantId))
      .filter(Boolean)
      .filter((variant) => !platformHealthMap[variant.platform]?.configured)
      .map((variant) => `${variant.platform} is not configured for live dispatch`);
  }, [platformHealthMap, selectedVariantIds, variants]);

  const filteredSchedules = useMemo(() => {
    if (scheduleFilter === 'all') return schedules;
    return schedules.filter((job) => job.platform === scheduleFilter || job.status === scheduleFilter);
  }, [scheduleFilter, schedules]);

  const filteredLogs = useMemo(() => {
    if (logFilter === 'all') return logs;
    return logs.filter((log) => log.platform === logFilter || log.status === logFilter || log.execution_mode === logFilter);
  }, [logFilter, logs]);

  useEffect(() => {
    loadDashboard();
  }, []);

  useEffect(() => {
    if (!selectedCampaignId) {
      setVariants([]);
      setAnalytics(null);
      setOptimization(null);
      setStrategy(null);
      setSelectedVariantIds([]);
      return;
    }
    loadCampaignWorkspace(selectedCampaignId);
  }, [selectedCampaignId]);

  async function loadDashboard() {
    setLoading(true);
    try {
      const [brandRes, campaignRes, scheduleRes, logRes, analyticsRes, healthRes, credentialRes] = await Promise.allSettled([
        marketingAPI.listBrandProfiles(),
        marketingAPI.listCampaigns(),
        marketingAPI.listSchedules(),
        marketingAPI.listDeliveryLogs(),
        marketingAPI.getAnalyticsSummary(),
        marketingAPI.getPlatformHealth(),
        marketingAPI.listChannelCredentials(),
      ]);
      const brandsData = settledData(brandRes, []);
      const campaignsData = settledData(campaignRes, []);
      const schedulesData = settledData(scheduleRes, []);
      const logsData = settledData(logRes, []);
      const analyticsData = settledData(analyticsRes, null);
      const healthData = settledData(healthRes, []);
      const credentialsData = settledData(credentialRes, []);
      const failures = [brandRes, campaignRes, scheduleRes, logRes, analyticsRes, healthRes, credentialRes].filter(
        (item) => item.status === 'rejected',
      );
      const hardFailure = failures.length === 7;

      startTransition(() => {
        setBrands(brandsData);
        setCampaigns(campaignsData);
        setSchedules(schedulesData);
        setLogs(logsData);
        setPlatformHealth(healthData);
        setChannelCredentials(credentialsData);
        setAnalytics(analyticsData);
      });
      if (hardFailure) {
        setWorkspaceNotice('Marketing backend is unreachable or not deployed with the latest routes yet.');
      } else if (failures.length) {
        setWorkspaceNotice('Agent loaded in fallback mode. Some marketing endpoints are unavailable, but the page is still usable.');
      } else {
        setWorkspaceNotice('');
      }
      if (!selectedBrandId && brandsData[0]) {
        setSelectedBrandId(brandsData[0].id);
      }
      if (!selectedCampaignId && campaignsData[0]) {
        setSelectedCampaignId(campaignsData[0].id);
      }
      if (hardFailure) {
        toast.error('Marketing backend is not reachable from the Agent page');
      }
    } catch (error) {
      setWorkspaceNotice('Marketing backend is unreachable or not deployed with the latest routes yet.');
      toast.error(readError(error, 'Failed to load agent workspace'));
    } finally {
      setLoading(false);
    }
  }

  async function loadCampaignWorkspace(campaignId) {
    setRefreshing(true);
    try {
      const [variantRes, analyticsRes] = await Promise.allSettled([
        marketingAPI.listVariants(campaignId),
        marketingAPI.getCampaignAnalytics(campaignId),
      ]);
      startTransition(() => {
        setVariants(settledData(variantRes, [], 'items'));
        setAnalytics(settledData(analyticsRes, analytics));
      });
      if (variantRes.status === 'rejected' || analyticsRes.status === 'rejected') {
        setWorkspaceNotice('Some campaign-level data could not be loaded. Backend routes may be incomplete.');
      }
    } catch (error) {
      toast.error(readError(error, 'Failed to load campaign workspace'));
    } finally {
      setRefreshing(false);
    }
  }

  async function handleBrandSubmit(event) {
    event.preventDefault();
    try {
      const payload = {
        brand_name: brandForm.brand_name.trim(),
        voice_style: brandForm.voice_style.trim(),
        preferred_vocabulary: splitList(brandForm.preferred_vocabulary),
        banned_phrases: splitList(brandForm.banned_phrases),
        signature_patterns: splitList(brandForm.signature_patterns),
        default_cta_style: brandForm.default_cta_style.trim(),
        audience_notes: brandForm.audience_notes.trim(),
        positioning: brandForm.positioning.trim(),
      };
      if (!payload.brand_name) {
        toast.error('Brand name is required');
        return;
      }
      const response = selectedBrandId
        ? await marketingAPI.updateBrandProfile(selectedBrandId, payload)
        : await marketingAPI.createBrandProfile(payload);
      const brand = response.data;
      setBrands((current) => {
        const exists = current.some((item) => item.id === brand.id);
        return exists ? current.map((item) => (item.id === brand.id ? brand : item)) : [brand, ...current];
      });
      setSelectedBrandId(brand.id);
      setCampaignForm((current) => ({ ...current, brand_profile_id: brand.id }));
      toast.success(selectedBrandId ? 'Brand brain updated' : 'Brand brain created');
    } catch (error) {
      toast.error(readError(error, 'Failed to save brand profile'));
    }
  }

  async function handleCampaignSubmit(event) {
    event.preventDefault();
    try {
      const payload = {
        ...campaignForm,
        brand_profile_id: campaignForm.brand_profile_id || null,
      };
      if (!payload.name.trim() || !payload.goal.trim()) {
        toast.error('Campaign name and goal are required');
        return;
      }
      const response = await marketingAPI.createCampaign(payload);
      const campaign = response.data;
      setCampaigns((current) => [campaign, ...current]);
      setSelectedCampaignId(campaign.id);
      setCampaignForm(defaultCampaignForm);
      toast.success('Campaign created');
    } catch (error) {
      toast.error(readError(error, 'Failed to create campaign'));
    }
  }

  async function handleGenerateStrategy() {
    if (!selectedCampaignId) {
      toast.error('Select a campaign first');
      return;
    }
    try {
      const response = await marketingAPI.generateStrategy(selectedCampaignId);
      setStrategy(response.data);
      toast.success('Strategy generated');
      await refreshCampaigns();
    } catch (error) {
      toast.error(readError(error, 'Failed to generate strategy'));
    }
  }

  async function handleGenerateVariants() {
    if (!selectedCampaignId) {
      toast.error('Select a campaign first');
      return;
    }
    try {
      const payload = {
        platforms: splitList(generationForm.platforms),
        experiment_labels: splitList(generationForm.experiment_labels) || ['A'],
        desired_tone: generationForm.desired_tone.trim(),
        cta_style: generationForm.cta_style.trim(),
        extra_context: splitList(generationForm.extra_context),
      };
      const response = await marketingAPI.generateVariants(selectedCampaignId, payload);
      setStrategy(response.data.strategy);
      setVariants(response.data.variants || []);
      setSelectedVariantIds([]);
      toast.success(`Generated ${response.data.variants?.length || 0} variants`);
      await refreshCampaigns();
    } catch (error) {
      toast.error(readError(error, 'Failed to generate variants'));
    }
  }

  async function handleVariantApproval(variantId, approved) {
    try {
      const response = await marketingAPI.approveVariant(variantId, approved);
      const { variant, reasons } = response.data;
      setVariants((current) => current.map((item) => (item.id === variant.id ? variant : item)));
      if (approved && reasons?.length) {
        toast.error(`Variant rejected: ${reasons.join(', ')}`);
        return;
      }
      toast.success(approved ? 'Variant approved' : 'Variant rejected');
    } catch (error) {
      toast.error(readError(error, 'Failed to review variant'));
    }
  }

  async function handleScheduleSelected() {
    if (!selectedCampaignId || !selectedVariantIds.length) {
      toast.error('Select at least one approved variant');
      return;
    }
    try {
      const response = await marketingAPI.scheduleCampaign(selectedCampaignId, {
        variant_ids: selectedVariantIds,
        run_at: new Date(scheduleAt).toISOString(),
        timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || 'Asia/Calcutta',
      });
      setSchedules((current) => [...response.data.jobs, ...current]);
      toast.success(`Scheduled ${response.data.jobs.length} jobs`);
      if (response.data.rejected_variant_ids?.length) {
        toast.error(`Rejected ${response.data.rejected_variant_ids.length} variants during scheduling`);
      }
    } catch (error) {
      toast.error(readError(error, 'Failed to schedule campaign'));
    }
  }

  async function handleDispatch(jobId, executionMode) {
    const job = schedules.find((item) => item.id === jobId);
    const health = job ? platformHealthMap[job.platform] : null;
    if (executionMode === 'live' && health && !health.configured) {
      toast.error(`${job.platform} is not configured for live dispatch`);
      return;
    }
    try {
      const response = await marketingAPI.dispatchJob(jobId, executionMode);
      setLogs((current) => [response.data, ...current]);
      toast.success(executionMode === 'live' ? 'Live dispatch completed' : 'Dry run completed');
      await refreshSchedules();
    } catch (error) {
      toast.error(readError(error, 'Failed to dispatch job'));
    }
  }

  async function handleScheduleStatus(jobId, nextAction) {
    try {
      const response = nextAction === 'pause'
        ? await marketingAPI.pauseSchedule(jobId)
        : await marketingAPI.resumeSchedule(jobId);
      const job = response.data;
      setSchedules((current) => current.map((item) => (item.id === job.id ? job : item)));
      toast.success(nextAction === 'pause' ? 'Job paused' : 'Job resumed');
    } catch (error) {
      toast.error(readError(error, 'Failed to update job status'));
    }
  }

  async function handleRecordPerformance(event) {
    event.preventDefault();
    if (!selectedCampaignId || !performanceForm.metric_value) {
      toast.error('Select a campaign and metric value');
      return;
    }
    try {
      await marketingAPI.recordPerformanceEvent({
        campaign_id: selectedCampaignId,
        variant_id: selectedVariantIds[0] || variants[0]?.id || null,
        platform: performanceForm.platform,
        metric_type: performanceForm.metric_type,
        metric_value: Number(performanceForm.metric_value),
        note: performanceForm.note.trim(),
        source: 'manual',
      });
      setPerformanceForm(defaultPerformanceForm);
      toast.success('Performance event recorded');
      await loadCampaignWorkspace(selectedCampaignId);
    } catch (error) {
      toast.error(readError(error, 'Failed to record performance event'));
    }
  }

  async function handleOptimize() {
    if (!selectedCampaignId) {
      toast.error('Select a campaign first');
      return;
    }
    try {
      const response = await marketingAPI.optimizeCampaign(selectedCampaignId);
      setOptimization(response.data);
      setAnalytics(response.data.analytics_summary);
      toast.success('Optimization updated');
      await loadCampaignWorkspace(selectedCampaignId);
    } catch (error) {
      toast.error(readError(error, 'Failed to optimize campaign'));
    }
  }

  async function refreshCampaigns() {
    const response = await marketingAPI.listCampaigns();
    setCampaigns(response.data || []);
  }

  async function refreshSchedules() {
    const response = await marketingAPI.listSchedules();
    setSchedules(response.data || []);
  }

  async function handleCredentialSave(event) {
    event.preventDefault();
    const allowedFields = platformCredentialFields[credentialPlatform] || [];
    const secrets = Object.fromEntries(
      allowedFields
        .map((field) => [field, credentialValues[field]?.trim() || ''])
        .filter(([, value]) => value),
    );
    if (!Object.keys(secrets).length) {
      toast.error('Enter at least one credential value');
      return;
    }
    try {
      const response = await marketingAPI.saveChannelCredentials({
        platform: credentialPlatform,
        account_label: credentialAccountLabel.trim() || 'default',
        secrets,
      });
      const saved = response.data;
      setChannelCredentials((current) => {
        const exists = current.some((item) => item.platform === saved.platform && item.account_label === saved.account_label);
        return exists
          ? current.map((item) => (item.platform === saved.platform && item.account_label === saved.account_label ? saved : item))
          : [...current, saved];
      });
      setCredentialValues({});
      toast.success('Credentials saved locally');
      const healthRes = await marketingAPI.getPlatformHealth();
      setPlatformHealth(healthRes.data || []);
    } catch (error) {
      toast.error(readError(error, 'Failed to save credentials'));
    }
  }

  function updateField(setter, key, value) {
    setter((current) => ({ ...current, [key]: value }));
  }

  function handleBrandSelection(brandId) {
    setSelectedBrandId(brandId);
    const brand = brands.find((item) => item.id === brandId);
    if (!brand) {
      setBrandForm(defaultBrandForm);
      return;
    }
    setBrandForm({
      brand_name: brand.brand_name || '',
      voice_style: brand.voice_style || '',
      preferred_vocabulary: (brand.preferred_vocabulary || []).join(', '),
      banned_phrases: (brand.banned_phrases || []).join(', '),
      signature_patterns: (brand.signature_patterns || []).join(', '),
      default_cta_style: brand.default_cta_style || '',
      audience_notes: brand.audience_notes || '',
      positioning: brand.positioning || '',
    });
    setCampaignForm((current) => ({ ...current, brand_profile_id: brand.id }));
  }

  function toggleVariantSelection(variantId) {
    setSelectedVariantIds((current) =>
      current.includes(variantId) ? current.filter((item) => item !== variantId) : [...current, variantId],
    );
  }

  function updateCredentialField(field, value) {
    setCredentialValues((current) => ({ ...current, [field]: value }));
  }

  return (
    <div className="pt-20 pb-20">
      <section className="px-6 pt-8">
        <div className="max-w-7xl mx-auto">
          {workspaceNotice ? (
            <div className="mb-4 rounded-3xl border border-[#bfa98b]/28 bg-[rgba(191,169,139,0.12)] px-5 py-4 text-sm leading-relaxed text-text-secondary">
              {workspaceNotice}
            </div>
          ) : null}
          <div className="glass-card p-8 md:p-10 overflow-hidden relative">
            <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(127,148,118,0.18),transparent_38%),radial-gradient(circle_at_bottom_right,rgba(191,169,139,0.16),transparent_34%)]" />
            <div className="relative z-10 flex flex-col gap-8 lg:flex-row lg:items-end lg:justify-between">
              <div className="max-w-3xl space-y-5">
                <div className="inline-flex items-center gap-2 rounded-full border border-black/5 bg-white/65 px-4 py-2 text-[11px] font-bold uppercase tracking-[0.2em] text-solace-purple">
                  <Radio className="h-3.5 w-3.5" />
                  <span>Autonomous Local Marketing Engine</span>
                </div>
                <div className="space-y-3">
                  <h1 className="text-4xl md:text-6xl font-bold tracking-tight leading-[0.95]">
                    Build, approve, schedule, and optimize campaigns from one Helix agent.
                  </h1>
                  <p className="max-w-2xl text-base md:text-lg text-text-secondary leading-relaxed">
                    This workspace runs your local marketing loop end to end: brand memory, campaign strategy, platform-specific variants,
                    execution queues, delivery logs, and feedback-driven optimization.
                  </p>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3 min-w-full lg:min-w-[360px] lg:max-w-[420px]">
                {summaryCards.map((card) => (
                  <div key={card.label} className={`rounded-3xl border border-black/5 bg-gradient-to-br ${card.tone} p-4 shadow-[0_20px_50px_rgba(55,62,54,0.08)]`}>
                    <div className="flex items-center justify-between text-text-muted">
                      <card.icon className="w-5 h-5" />
                      <ChevronRight className="w-4 h-4" />
                    </div>
                    <div className="mt-5 text-3xl font-bold text-text-primary">{card.value}</div>
                    <div className="mt-1 text-xs font-bold uppercase tracking-[0.18em] text-text-muted">{card.label}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>
      <section className="px-6 mt-8">
        <div className="max-w-7xl mx-auto grid grid-cols-1 xl:grid-cols-[1.1fr_0.9fr] gap-6">
          <div className="space-y-6">
            <Panel
              title="Brand Brain"
              icon={Brain}
              action={(
                <select
                  value={selectedBrandId}
                  onChange={(event) => handleBrandSelection(event.target.value)}
                  className="rounded-2xl border border-black/8 bg-white/80 px-4 py-2 text-sm text-text-primary outline-none"
                >
                  <option value="">New profile</option>
                  {brands.map((brand) => (
                    <option key={brand.id} value={brand.id}>{brand.brand_name}</option>
                  ))}
                </select>
              )}
            >
              <form className="grid grid-cols-1 md:grid-cols-2 gap-4" onSubmit={handleBrandSubmit}>
                <Input label="Brand Name" value={brandForm.brand_name} onChange={(value) => updateField(setBrandForm, 'brand_name', value)} required />
                <Input label="CTA Style" value={brandForm.default_cta_style} onChange={(value) => updateField(setBrandForm, 'default_cta_style', value)} />
                <Input label="Voice Style" value={brandForm.voice_style} onChange={(value) => updateField(setBrandForm, 'voice_style', value)} className="md:col-span-2" />
                <Input label="Preferred Vocabulary" value={brandForm.preferred_vocabulary} onChange={(value) => updateField(setBrandForm, 'preferred_vocabulary', value)} hint="Comma separated" />
                <Input label="Banned Phrases" value={brandForm.banned_phrases} onChange={(value) => updateField(setBrandForm, 'banned_phrases', value)} hint="Comma separated" />
                <Input label="Signature Patterns" value={brandForm.signature_patterns} onChange={(value) => updateField(setBrandForm, 'signature_patterns', value)} hint="Comma separated" className="md:col-span-2" />
                <Textarea label="Audience Notes" value={brandForm.audience_notes} onChange={(value) => updateField(setBrandForm, 'audience_notes', value)} />
                <Textarea label="Positioning" value={brandForm.positioning} onChange={(value) => updateField(setBrandForm, 'positioning', value)} />
                <div className="md:col-span-2 flex justify-end">
                  <button type="submit" className="btn-solace-primary !py-3 !px-6 text-sm">
                    {selectedBrandId ? 'Update Brand Brain' : 'Create Brand Brain'}
                  </button>
                </div>
              </form>
            </Panel>

            <Panel title="Campaign Builder" icon={FileText}>
              <form className="grid grid-cols-1 md:grid-cols-2 gap-4" onSubmit={handleCampaignSubmit}>
                <Input label="Campaign Name" value={campaignForm.name} onChange={(value) => updateField(setCampaignForm, 'name', value)} required />
                <Input label="Target Audience" value={campaignForm.target_audience} onChange={(value) => updateField(setCampaignForm, 'target_audience', value)} />
                <Input label="Brand Voice Override" value={campaignForm.brand_voice} onChange={(value) => updateField(setCampaignForm, 'brand_voice', value)} />
                <div className="space-y-2">
                  <label className="text-xs font-bold uppercase tracking-[0.18em] text-text-muted">Brand Profile</label>
                  <select
                    value={campaignForm.brand_profile_id}
                    onChange={(event) => updateField(setCampaignForm, 'brand_profile_id', event.target.value)}
                    className="input-solace !px-4 !py-3"
                  >
                    <option value="">No linked brand</option>
                    {brands.map((brand) => (
                      <option key={brand.id} value={brand.id}>{brand.brand_name}</option>
                    ))}
                  </select>
                </div>
                <Textarea label="Goal" value={campaignForm.goal} onChange={(value) => updateField(setCampaignForm, 'goal', value)} className="md:col-span-2" required />
                <Textarea label="Offer Summary" value={campaignForm.offer_summary} onChange={(value) => updateField(setCampaignForm, 'offer_summary', value)} className="md:col-span-2" />
                <div className="md:col-span-2 flex justify-end">
                  <button type="submit" className="btn-solace-primary !py-3 !px-6 text-sm">Create Campaign</button>
                </div>
              </form>

              <div className="mt-6 grid gap-3">
                {campaigns.map((campaign) => (
                  <button
                    key={campaign.id}
                    onClick={() => setSelectedCampaignId(campaign.id)}
                    className={`w-full rounded-3xl border px-5 py-4 text-left transition-all duration-300 ${
                      selectedCampaignId === campaign.id
                        ? 'border-solace-purple/30 bg-white shadow-[0_16px_35px_rgba(79,89,75,0.08)]'
                        : 'border-black/5 bg-[rgba(255,252,247,0.55)] hover:bg-white/80'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div className="space-y-2">
                        <div className="text-lg font-bold text-text-primary">{campaign.name}</div>
                        <div className="text-sm text-text-secondary leading-relaxed">{campaign.goal}</div>
                      </div>
                      <span className="rounded-full bg-[#e8e1d5] px-3 py-1 text-[10px] font-bold uppercase tracking-[0.18em] text-text-muted">
                        {campaign.status}
                      </span>
                    </div>
                  </button>
                ))}
              </div>
            </Panel>
          </div>

          <div className="space-y-6">
            <Panel
              title="Agent Runbook"
              icon={Sparkles}
              action={(
                <button
                  type="button"
                  onClick={loadDashboard}
                  className="rounded-2xl border border-black/8 bg-white/75 p-2 text-text-secondary transition-colors hover:text-text-primary"
                  title="Refresh workspace"
                >
                  <RefreshCw className={`w-4 h-4 ${refreshing || loading ? 'animate-spin' : ''}`} />
                </button>
              )}
            >
              {selectedCampaign ? (
                <div className="space-y-6">
                  <div className="rounded-3xl bg-[rgba(255,252,247,0.72)] border border-black/5 p-5">
                    <div className="flex items-center justify-between gap-4">
                      <div>
                        <div className="text-xs font-bold uppercase tracking-[0.18em] text-text-muted">Selected Campaign</div>
                        <div className="mt-2 text-2xl font-bold text-text-primary">{selectedCampaign.name}</div>
                      </div>
                      <div className="rounded-2xl bg-[#ece6db] px-4 py-2 text-xs font-bold uppercase tracking-[0.18em] text-text-muted">
                        {selectedCampaign.status}
                      </div>
                    </div>
                    <p className="mt-3 text-sm text-text-secondary leading-relaxed">{selectedCampaign.goal}</p>
                  </div>

                  <div className="flex flex-wrap gap-3">
                    <button type="button" onClick={handleGenerateStrategy} className="btn-solace-outline !py-3 !px-5 text-sm">Generate Strategy</button>
                    <button type="button" onClick={handleGenerateVariants} className="btn-solace-primary !py-3 !px-5 text-sm">Generate Variants</button>
                    <button type="button" onClick={handleOptimize} className="btn-solace-outline !py-3 !px-5 text-sm">Optimize</button>
                  </div>

                  <div className="grid grid-cols-1 gap-4">
                    <Input label="Platforms" value={generationForm.platforms} onChange={(value) => updateField(setGenerationForm, 'platforms', value)} hint="linkedin, x, telegram, webhook, email" />
                    <Input label="Experiment Labels" value={generationForm.experiment_labels} onChange={(value) => updateField(setGenerationForm, 'experiment_labels', value)} hint="A,B" />
                    <Input label="Desired Tone" value={generationForm.desired_tone} onChange={(value) => updateField(setGenerationForm, 'desired_tone', value)} />
                    <Input label="CTA Style" value={generationForm.cta_style} onChange={(value) => updateField(setGenerationForm, 'cta_style', value)} />
                    <Textarea label="Extra Context" value={generationForm.extra_context} onChange={(value) => updateField(setGenerationForm, 'extra_context', value)} hint="Comma separated notes or constraints" />
                  </div>

                  {strategy && (
                    <div className="rounded-3xl border border-black/5 bg-[#fffcf7] p-5 space-y-3">
                      <div className="flex items-center gap-2 text-sm font-bold text-text-primary">
                        <ShieldCheck className="w-4 h-4 text-solace-purple" />
                        <span>Current Strategy</span>
                      </div>
                      <p className="text-sm text-text-secondary leading-relaxed">{strategy.strategy_summary}</p>
                      <div className="flex flex-wrap gap-2">
                        {strategy.primary_platforms.map((platform) => <Tag key={platform}>{platform}</Tag>)}
                        <Tag>{strategy.posting_frequency}</Tag>
                        <Tag>{strategy.tone_direction}</Tag>
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <EmptyState icon={Bot} title="No campaign selected" description="Create a campaign or choose one from the builder to start the agent workflow." />
              )}
            </Panel>

            <Panel title="Variants and Approval" icon={Activity}>
              {variants.length ? (
                <div className="space-y-4">
                  {variants.map((variant) => (
                    <motion.div
                      key={variant.id}
                      initial={{ opacity: 0, y: 6 }}
                      animate={{ opacity: 1, y: 0 }}
                      className="rounded-3xl border border-black/5 bg-[rgba(255,252,247,0.8)] p-5"
                    >
                      <div className="flex items-start justify-between gap-4">
                        <div className="space-y-2">
                          <div className="flex flex-wrap gap-2">
                            <Tag>{variant.platform}</Tag>
                            <Tag>{variant.experiment_group || 'A'}</Tag>
                            <Tag>{variant.approval_status}</Tag>
                          </div>
                          <div className="text-lg font-bold text-text-primary">{variant.variant_name}</div>
                        </div>
                        <label className="inline-flex items-center gap-2 rounded-full border border-black/8 bg-white px-3 py-2 text-xs font-bold uppercase tracking-[0.16em] text-text-muted">
                          <input
                            type="checkbox"
                            checked={selectedVariantIds.includes(variant.id)}
                            onChange={() => toggleVariantSelection(variant.id)}
                            className="h-4 w-4 rounded border-black/10"
                          />
                          Select
                        </label>
                      </div>
                      <pre className="mt-4 whitespace-pre-wrap text-sm leading-relaxed text-text-secondary font-sans">{variant.generated_text}</pre>
                      <div className="mt-4 flex flex-wrap gap-3">
                        <button type="button" onClick={() => handleVariantApproval(variant.id, true)} className="btn-solace-primary !py-2.5 !px-4 text-sm">Approve</button>
                        <button type="button" onClick={() => handleVariantApproval(variant.id, false)} className="btn-solace-outline !py-2.5 !px-4 text-sm">Reject</button>
                      </div>
                    </motion.div>
                  ))}
                </div>
              ) : (
                <EmptyState icon={Sparkles} title="No variants generated yet" description="Run strategy and generation to create platform-specific campaign variants." />
              )}
            </Panel>

            <Panel title="Scheduler, Delivery, and Learning" icon={Clock3}>
              <div className="space-y-6">
                <div className="rounded-3xl border border-black/5 bg-[rgba(255,252,247,0.76)] p-5 space-y-4">
                  <div className="text-sm font-bold text-text-primary">Schedule Approved Variants</div>
                  {selectedVariantWarnings.length ? (
                    <div className="rounded-2xl border border-[#bfa98b]/30 bg-[rgba(191,169,139,0.12)] px-4 py-3 text-xs text-text-secondary">
                      {selectedVariantWarnings.join(' | ')}
                    </div>
                  ) : null}
                  <div className="grid grid-cols-1 md:grid-cols-[1fr_auto] gap-3">
                    <input
                      type="datetime-local"
                      value={scheduleAt}
                      onChange={(event) => setScheduleAt(event.target.value)}
                      className="input-solace !px-4 !py-3"
                    />
                    <button type="button" onClick={handleScheduleSelected} className="btn-solace-primary !py-3 !px-5 text-sm">Schedule Selected</button>
                  </div>
                </div>

                <form onSubmit={handleRecordPerformance} className="rounded-3xl border border-black/5 bg-[rgba(255,252,247,0.76)] p-5 space-y-4">
                  <div className="text-sm font-bold text-text-primary">Manual Performance Signal</div>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                    <Input label="Platform" value={performanceForm.platform} onChange={(value) => updateField(setPerformanceForm, 'platform', value)} />
                    <Input label="Metric Type" value={performanceForm.metric_type} onChange={(value) => updateField(setPerformanceForm, 'metric_type', value)} />
                    <Input label="Metric Value" value={performanceForm.metric_value} onChange={(value) => updateField(setPerformanceForm, 'metric_value', value)} />
                  </div>
                  <Textarea label="Note" value={performanceForm.note} onChange={(value) => updateField(setPerformanceForm, 'note', value)} />
                  <div className="flex justify-end">
                    <button type="submit" className="btn-solace-outline !py-3 !px-5 text-sm">Record Signal</button>
                  </div>
                </form>

                {optimization && (
                  <div className="rounded-3xl border border-black/5 bg-white p-5 space-y-3">
                    <div className="flex items-center gap-2 text-sm font-bold text-text-primary">
                      <LineChart className="w-4 h-4 text-solace-blue" />
                      <span>Optimization Output</span>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                      <Metric label="Top Platform" value={optimization.top_platform} />
                      <Metric label="CTA Direction" value={optimization.recommended_cta_style} />
                      <Metric label="Posting Window" value={optimization.recommended_posting_window} />
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {(optimization.prompt_bias_hints || []).map((hint) => <Tag key={hint}>{hint}</Tag>)}
                    </div>
                  </div>
                )}

                <div className="grid grid-cols-1 gap-4">
                  <SubPanel title="Platform Readiness">
                    {platformHealth.length ? (
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                        {platformHealth.map((item) => (
                          <div
                            key={item.platform}
                            className={`rounded-2xl border px-4 py-4 ${
                              item.configured
                                ? 'border-[#7f9476]/18 bg-[rgba(127,148,118,0.08)]'
                                : 'border-[#bfa98b]/18 bg-[rgba(191,169,139,0.08)]'
                            }`}
                          >
                            <div className="flex items-center justify-between gap-3">
                              <div className="text-sm font-semibold uppercase tracking-[0.16em] text-text-primary">
                                {item.platform}
                              </div>
                              <span
                                className={`rounded-full px-2.5 py-1 text-[10px] font-bold uppercase tracking-[0.16em] ${
                                  item.configured
                                    ? 'bg-[#7f9476] text-white'
                                    : 'bg-[#bfa98b] text-white'
                                }`}
                              >
                                {item.configured ? 'Live Ready' : 'Needs Config'}
                              </span>
                            </div>
                            <div className="mt-3 text-xs leading-relaxed text-text-secondary">
                              {item.message || 'No status detail available.'}
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <MiniEmpty>No adapter health data yet.</MiniEmpty>
                    )}
                  </SubPanel>

                  <SubPanel title="Operator Settings">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      {Object.entries(platformEnvHints).map(([platform, keys]) => {
                        const status = platformHealthMap[platform];
                        return (
                          <div key={platform} className="rounded-2xl border border-black/5 bg-white/80 px-4 py-4">
                            <div className="flex items-center justify-between gap-3">
                              <div className="text-sm font-semibold uppercase tracking-[0.16em] text-text-primary">{platform}</div>
                              <span className={`rounded-full px-2.5 py-1 text-[10px] font-bold uppercase tracking-[0.16em] ${
                                status?.configured ? 'bg-[#7f9476] text-white' : 'bg-[#ece6db] text-text-muted'
                              }`}>
                                {status?.configured ? 'Configured' : 'Pending'}
                              </span>
                            </div>
                            <div className="mt-3 space-y-1">
                              {keys.map((key) => (
                                <div key={key} className="text-xs text-text-secondary">{key}</div>
                              ))}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                    <form onSubmit={handleCredentialSave} className="mt-4 rounded-2xl border border-black/5 bg-[rgba(255,252,247,0.76)] p-4 space-y-4">
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                        <div className="space-y-2">
                          <label className="text-xs font-bold uppercase tracking-[0.18em] text-text-muted">Platform</label>
                          <select
                            value={credentialPlatform}
                            onChange={(event) => {
                              setCredentialPlatform(event.target.value);
                              setCredentialValues({});
                            }}
                            className="input-solace !px-4 !py-3"
                          >
                            {Object.keys(platformCredentialFields).map((platform) => (
                              <option key={platform} value={platform}>{platform}</option>
                            ))}
                          </select>
                        </div>
                        <Input label="Account Label" value={credentialAccountLabel} onChange={setCredentialAccountLabel} />
                      </div>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                        {(platformCredentialFields[credentialPlatform] || []).map((field) => (
                          <Input
                            key={field}
                            label={field}
                            value={credentialValues[field] || ''}
                            onChange={(value) => updateCredentialField(field, value)}
                          />
                        ))}
                      </div>
                      <div className="flex justify-end">
                        <button type="submit" className="btn-solace-primary !py-3 !px-5 text-sm">Save Local Credentials</button>
                      </div>
                    </form>
                    <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-3">
                      {channelCredentials.map((item) => (
                        <div key={`${item.platform}-${item.account_label}`} className="rounded-2xl border border-black/5 bg-white/75 px-4 py-4">
                          <div className="flex items-center justify-between gap-3">
                            <div className="text-sm font-semibold text-text-primary">{item.platform}</div>
                            <span className="text-[10px] font-bold uppercase tracking-[0.16em] text-text-muted">{item.account_label}</span>
                          </div>
                          <div className="mt-3 flex flex-wrap gap-2">
                            {(item.configured_fields || []).map((field) => (
                              <Tag key={`${item.platform}-${field}`}>{field}</Tag>
                            ))}
                          </div>
                        </div>
                      ))}
                    </div>
                  </SubPanel>

                  <SubPanel title="Scheduled Jobs">
                    <div className="mb-4">
                      <select
                        value={scheduleFilter}
                        onChange={(event) => setScheduleFilter(event.target.value)}
                        className="rounded-xl border border-black/8 bg-white/80 px-3 py-2 text-xs font-bold uppercase tracking-[0.16em] text-text-primary outline-none"
                      >
                        <option value="all">All Schedules</option>
                        <option value="queued">Queued</option>
                        <option value="pending">Pending</option>
                        <option value="running">Running</option>
                        <option value="completed">Completed</option>
                        <option value="failed">Failed</option>
                        <option value="paused">Paused</option>
                        {platformHealth.map((item) => (
                          <option key={`schedule-${item.platform}`} value={item.platform}>{item.platform}</option>
                        ))}
                      </select>
                    </div>
                    {filteredSchedules.slice(0, 5).map((job) => (
                      <ListRow
                        key={job.id}
                        title={`${job.platform} - ${job.status}`}
                        meta={new Date(job.run_at).toLocaleString()}
                        action={(
                          <div className="flex gap-2">
                            <button type="button" onClick={() => handleDispatch(job.id, 'dry_run')} className="rounded-xl border border-black/8 bg-white px-3 py-2 text-xs font-bold text-text-primary">Dry Run</button>
                            <button
                              type="button"
                              onClick={() => handleDispatch(job.id, 'live')}
                              disabled={!platformHealthMap[job.platform]?.configured}
                              className={`rounded-xl px-3 py-2 text-xs font-bold ${
                                platformHealthMap[job.platform]?.configured
                                  ? 'bg-[#6d7b68] text-white'
                                  : 'bg-[#ece6db] text-text-muted cursor-not-allowed'
                              }`}
                            >
                              Live
                            </button>
                            {job.status === 'paused' ? (
                              <button type="button" onClick={() => handleScheduleStatus(job.id, 'resume')} className="rounded-xl border border-black/8 bg-white px-3 py-2 text-xs font-bold text-text-primary">Resume</button>
                            ) : (
                              <button type="button" onClick={() => handleScheduleStatus(job.id, 'pause')} className="rounded-xl border border-black/8 bg-white px-3 py-2 text-xs font-bold text-text-primary">Pause</button>
                            )}
                          </div>
                        )}
                      />
                    ))}
                    {!filteredSchedules.length && <MiniEmpty>No scheduled jobs for this filter.</MiniEmpty>}
                  </SubPanel>

                  <SubPanel title="Delivery Logs">
                    <div className="mb-4">
                      <select
                        value={logFilter}
                        onChange={(event) => setLogFilter(event.target.value)}
                        className="rounded-xl border border-black/8 bg-white/80 px-3 py-2 text-xs font-bold uppercase tracking-[0.16em] text-text-primary outline-none"
                      >
                        <option value="all">All Logs</option>
                        <option value="dry_run">Dry Run</option>
                        <option value="live">Live</option>
                        <option value="failed">Failed</option>
                        <option value="sent">Sent</option>
                        {platformHealth.map((item) => (
                          <option key={`log-${item.platform}`} value={item.platform}>{item.platform}</option>
                        ))}
                      </select>
                    </div>
                    {filteredLogs.slice(0, 5).map((log) => (
                      <ListRow
                        key={log.id}
                        title={`${log.platform} - ${log.status}`}
                        meta={`${log.execution_mode} - ${new Date(log.created_at).toLocaleString()}`}
                        action={<Send className="w-4 h-4 text-text-muted" />}
                      />
                    ))}
                    {!filteredLogs.length && <MiniEmpty>No delivery logs for this filter.</MiniEmpty>}
                  </SubPanel>

                  <SubPanel title="Analytics Snapshot">
                    {analytics ? (
                      <div className="space-y-4">
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                          <Metric label="Events" value={analytics.total_events} />
                          <Metric label="Platforms" value={Object.keys(analytics.platform_scores || {}).length} />
                          <Metric label="Hints" value={(analytics.memory_hints || []).length} />
                        </div>
                        <div className="flex flex-wrap gap-2">
                          {(analytics.memory_hints || []).map((hint) => <Tag key={hint}>{hint}</Tag>)}
                        </div>
                      </div>
                    ) : (
                      <MiniEmpty>No analytics yet.</MiniEmpty>
                    )}
                  </SubPanel>
                </div>
              </div>
            </Panel>
          </div>
        </div>
      </section>
    </div>
  );
};

const Panel = ({ title, icon: Icon, action, children }) => (
  <div className="glass-card p-6 md:p-7">
    <div className="flex items-center justify-between gap-4 mb-6">
      <div className="flex items-center gap-3">
        <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-white/70 border border-black/5">
          <Icon className="w-5 h-5 text-solace-purple" />
        </div>
        <h2 className="text-xl font-bold text-text-primary">{title}</h2>
      </div>
      {action}
    </div>
    {children}
  </div>
);

const SubPanel = ({ title, children }) => (
  <div className="rounded-3xl border border-black/5 bg-[rgba(255,252,247,0.68)] p-5">
    <div className="mb-4 text-sm font-bold text-text-primary">{title}</div>
    {children}
  </div>
);

const Input = ({ label, value, onChange, hint, required = false, className = '' }) => (
  <div className={`space-y-2 ${className}`}>
    <label className="text-xs font-bold uppercase tracking-[0.18em] text-text-muted">{label}</label>
    <input
      value={value}
      required={required}
      onChange={(event) => onChange(event.target.value)}
      className="input-solace !px-4 !py-3"
    />
    {hint ? <div className="text-[11px] text-text-muted">{hint}</div> : null}
  </div>
);

const Textarea = ({ label, value, onChange, hint, required = false, className = '' }) => (
  <div className={`space-y-2 ${className}`}>
    <label className="text-xs font-bold uppercase tracking-[0.18em] text-text-muted">{label}</label>
    <textarea
      value={value}
      required={required}
      onChange={(event) => onChange(event.target.value)}
      rows={4}
      className="input-solace !px-4 !py-3 resize-y min-h-[120px]"
    />
    {hint ? <div className="text-[11px] text-text-muted">{hint}</div> : null}
  </div>
);

const Tag = ({ children }) => (
  <span className="rounded-full bg-[#ebe3d6] px-3 py-1 text-[10px] font-bold uppercase tracking-[0.18em] text-text-muted">
    {children}
  </span>
);

const Metric = ({ label, value }) => (
  <div className="rounded-2xl border border-black/5 bg-white/80 px-4 py-4">
    <div className="text-[11px] font-bold uppercase tracking-[0.18em] text-text-muted">{label}</div>
    <div className="mt-2 text-xl font-bold text-text-primary">{value}</div>
  </div>
);

const ListRow = ({ title, meta, action }) => (
  <div className="flex items-center justify-between gap-4 rounded-2xl border border-black/5 bg-white/80 px-4 py-3">
    <div className="space-y-1">
      <div className="text-sm font-semibold text-text-primary">{title}</div>
      <div className="text-xs text-text-muted">{meta}</div>
    </div>
    {action}
  </div>
);

const EmptyState = ({ icon: Icon, title, description }) => (
  <div className="rounded-3xl border border-dashed border-black/10 bg-[rgba(255,252,247,0.46)] px-6 py-10 text-center">
    <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-white/80 border border-black/5">
      <Icon className="w-6 h-6 text-solace-purple" />
    </div>
    <h3 className="mt-4 text-lg font-bold text-text-primary">{title}</h3>
    <p className="mt-2 text-sm leading-relaxed text-text-secondary max-w-sm mx-auto">{description}</p>
  </div>
);

const MiniEmpty = ({ children }) => (
  <div className="rounded-2xl border border-dashed border-black/10 px-4 py-5 text-sm text-text-secondary">{children}</div>
);

function splitList(value) {
  return value
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean);
}

function readError(error, fallback) {
  return error?.response?.data?.detail || error?.message || fallback;
}

export default AgentPage;
