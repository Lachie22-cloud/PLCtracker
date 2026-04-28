export type NpdStatus = 'in_progress' | 'on_hold' | 'completed' | 'cancelled';
export type StepStatus = 'not_started' | 'in_progress' | 'completed' | 'blocked' | 'n_a';

export interface NpdStep {
  id: string;
  label: string;
  desc: string;
}

export interface NpdComment {
  who: string;
  when: string;
  text: string;
}

export interface NpdEmail {
  when: string;
  subject: string;
  matched_step: string;
  note: string;
}

export interface NpdRequest {
  no: string;
  type: 'Bulk + FG' | 'FG Only' | 'Bulk Only';
  from: string;
  division: string;
  bulk_sku: string;
  fg_sku: string;
  warehouse_plants: string[];
  target: string;
  entered_by: string;
  created: string;
  status: NpdStatus;
  notes: string;
  progress: Record<string, StepStatus>;
  governance_violations: number;
  completed_by: Record<string, string>;
  comments: NpdComment[];
  emails: NpdEmail[];
}

export interface StatusMeta {
  label: string;
  badge: string;
}

export interface StepMeta {
  label: string;
  color: string;
}

export const NPD_STEPS: NpdStep[] = [
  { id:'intake',       label:'Intake & Triage',          desc:'Request received, type confirmed, division assigned.' },
  { id:'spec',         label:'Specification Drafted',    desc:'Bulk and FG specs drafted by R&D.' },
  { id:'spec_signoff', label:'Specification Sign-Off',   desc:'Marketing and Regulatory approve the spec.' },
  { id:'matnr',        label:'Material Numbers Created', desc:'MARA + MARC records created in SAP.' },
  { id:'governance',   label:'Governance Validated',     desc:'All preset critical fields pass.' },
  { id:'batch',        label:'Batch Raised',             desc:'First production batch raised. Capture batch no.' },
  { id:'batch_sched',  label:'Batch Scheduled',          desc:'Batch slotted into factory schedule.' },
  { id:'batch_done',   label:'First Batch Completed',    desc:'First good production passed QA.' },
  { id:'warehouse',    label:'Warehouse Receipt',        desc:'Stock physically received at warehouse plants.' },
  { id:'live',         label:'Available to Sell',        desc:'Sales-org released, ATP returns positive.' },
];

export const NPD_STATUS_META: Record<string, StatusMeta> = {
  in_progress: { label: 'In Progress', badge: 'running' },
  on_hold:     { label: 'On Hold',     badge: 'warning' },
  completed:   { label: 'Completed',   badge: 'ok' },
  cancelled:   { label: 'Cancelled',   badge: '' },
};

export const STEP_STATUS_META: Record<string, StepMeta> = {
  not_started: { label: 'Not started', color: 'muted'    },
  in_progress: { label: 'In progress', color: 'info'     },
  completed:   { label: 'Completed',   color: 'ok'       },
  blocked:     { label: 'Blocked',     color: 'critical' },
  n_a:         { label: 'N/A',         color: 'n_a'      },
};

export const stepProgress = (req: NpdRequest) => {
  const ordered = NPD_STEPS.map(s => req.progress[s.id]);
  const total = ordered.filter(s => s !== 'n_a').length;
  const done  = ordered.filter(s => s === 'completed').length;
  const next  = NPD_STEPS.find(s => {
    const st = req.progress[s.id];
    return st !== 'completed' && st !== 'n_a';
  });
  return { done, total, next };
};

export const daysOpen = (createdISO: string) => {
  const ms = Date.now() - new Date(createdISO).getTime();
  return Math.max(0, Math.floor(ms / 86400000));
};

export const NPD: NpdRequest[] = [
  {
    no:'NPD-2026-001',type:'Bulk + FG',from:'Marc Lapierre',division:'54',
    bulk_sku:'MAT-018442',fg_sku:'MAT-018443',warehouse_plants:['DC10','DC20'],
    target:'2026-06-15',entered_by:'Anya Krause',created:'2026-04-08',status:'in_progress',
    notes:'Bulk reformulation for Q3 colour pop programme. Fast-track if possible.',
    progress:{intake:'completed',spec:'completed',spec_signoff:'completed',matnr:'completed',governance:'completed',batch:'in_progress',batch_sched:'not_started',batch_done:'not_started',warehouse:'not_started',live:'not_started'},
    governance_violations:0,
    completed_by:{intake:'Anya K. · 8 Apr',spec:'R&D-54 · 11 Apr',spec_signoff:'M. Hansen · 18 Apr',matnr:'SAP-bot · 21 Apr',governance:'Lena D. · 22 Apr'},
    comments:[
      {who:'Anya Krause',when:'2026-04-08T09:14:00Z',text:'Logged. Marc requested fast-track — flagged with R&D.'},
      {who:'Lena Decker',when:'2026-04-22T14:02:00Z',text:'Governance check clean. All 4 critical fields OK on QF00.'},
    ],
    emails:[
      {when:'2026-04-21T11:08:00Z',subject:'Re: SAP MATNR for NPD-2026-001',matched_step:'matnr',note:'Step marked completed.'},
      {when:'2026-04-25T16:42:00Z',subject:'Batch raised — confirmation',matched_step:'batch',note:'Status set to in_progress.'},
    ],
  },
  {
    no:'NPD-2026-002',type:'FG Only',from:'Priya Iyer',division:'75',
    bulk_sku:'—',fg_sku:'MAT-018501',warehouse_plants:['DC30'],
    target:'2026-05-30',entered_by:'Tom Rae',created:'2026-04-02',status:'in_progress',
    progress:{intake:'completed',spec:'completed',spec_signoff:'completed',matnr:'completed',governance:'blocked',batch:'n_a',batch_sched:'n_a',batch_done:'n_a',warehouse:'not_started',live:'not_started'},
    governance_violations:2,
    completed_by:{intake:'Tom R. · 2 Apr',spec:'R&D-75 · 9 Apr',spec_signoff:'P. Iyer · 14 Apr',matnr:'SAP-bot · 18 Apr'},
    notes:'FG-only — bulk supplied from Avista contract manufacturer.',
    comments:[{who:'Tom Rae',when:'2026-04-18T10:12:00Z',text:'MATNR created, governance failing on DISPR + MTVFP at DC30.'}],
    emails:[],
  },
  {
    no:'NPD-2026-003',type:'Bulk Only',from:'Karl Brandt',division:'55',
    bulk_sku:'MAT-018622',fg_sku:'—',warehouse_plants:[],
    target:'2026-07-01',entered_by:'Anya Krause',created:'2026-04-15',status:'in_progress',
    progress:{intake:'completed',spec:'completed',spec_signoff:'in_progress',matnr:'not_started',governance:'not_started',batch:'not_started',batch_sched:'not_started',batch_done:'not_started',warehouse:'n_a',live:'n_a'},
    governance_violations:0,
    completed_by:{intake:'Anya K. · 15 Apr',spec:'R&D-55 · 19 Apr'},
    notes:'Bulk-only intermediate for PC-55 reformulation. No FG yet.',
    comments:[],emails:[],
  },
  {
    no:'NPD-2026-004',type:'Bulk + FG',from:'Amelia Reyes',division:'54',
    bulk_sku:'MAT-018744',fg_sku:'MAT-018745',warehouse_plants:['DC10'],
    target:'2026-08-12',entered_by:'Tom Rae',created:'2026-04-19',status:'on_hold',
    progress:{intake:'completed',spec:'in_progress',spec_signoff:'not_started',matnr:'not_started',governance:'not_started',batch:'not_started',batch_sched:'not_started',batch_done:'not_started',warehouse:'not_started',live:'not_started'},
    governance_violations:0,
    completed_by:{intake:'Tom R. · 19 Apr'},
    notes:'On hold pending pigment supplier confirmation.',
    comments:[{who:'Amelia Reyes',when:'2026-04-23T15:30:00Z',text:'Holding until pigment substitution decision.'}],
    emails:[],
  },
  {
    no:'NPD-2026-005',type:'FG Only',from:'Joaquim Silva',division:'75',
    bulk_sku:'—',fg_sku:'MAT-017990',warehouse_plants:['DC20','DC30'],
    target:'2026-04-15',entered_by:'Anya Krause',created:'2026-03-04',status:'completed',
    progress:{intake:'completed',spec:'completed',spec_signoff:'completed',matnr:'completed',governance:'completed',batch:'completed',batch_sched:'completed',batch_done:'completed',warehouse:'completed',live:'completed'},
    governance_violations:0,
    completed_by:{intake:'Anya K. · 4 Mar',spec:'R&D-75 · 10 Mar',spec_signoff:'P. Iyer · 14 Mar',matnr:'SAP-bot · 18 Mar',governance:'Lena D. · 19 Mar',batch:'Plant QF00 · 22 Mar',batch_sched:'QF00 · 24 Mar',batch_done:'QA-QF00 · 1 Apr',warehouse:'DC20 · 8 Apr',live:'SD-bot · 12 Apr'},
    notes:'Closed out cleanly. Reference for documentation team.',
    comments:[],emails:[],
  },
  {
    no:'NPD-2026-006',type:'Bulk + FG',from:'Sara Mitchell',division:'55',
    bulk_sku:'MAT-018880',fg_sku:'MAT-018881',warehouse_plants:['DC10'],
    target:'2026-05-10',entered_by:'Tom Rae',created:'2026-04-21',status:'in_progress',
    progress:{intake:'completed',spec:'completed',spec_signoff:'completed',matnr:'in_progress',governance:'not_started',batch:'not_started',batch_sched:'not_started',batch_done:'not_started',warehouse:'not_started',live:'not_started'},
    governance_violations:0,
    completed_by:{intake:'Tom R. · 21 Apr',spec:'R&D-55 · 23 Apr',spec_signoff:'K. Brandt · 25 Apr'},
    notes:'PC-55 line extension.',
    comments:[],emails:[],
  },
  {
    no:'NPD-2026-007',type:'Bulk Only',from:'Marc Lapierre',division:'54',
    bulk_sku:'MAT-018940',fg_sku:'—',warehouse_plants:[],
    target:'2026-04-05',entered_by:'Anya Krause',created:'2026-02-18',status:'cancelled',
    progress:{intake:'completed',spec:'completed',spec_signoff:'completed',matnr:'completed',governance:'not_started',batch:'not_started',batch_sched:'not_started',batch_done:'not_started',warehouse:'n_a',live:'n_a'},
    governance_violations:0,
    completed_by:{intake:'Anya K. · 18 Feb',spec:'R&D-54 · 25 Feb',spec_signoff:'M. Hansen · 3 Mar',matnr:'SAP-bot · 8 Mar'},
    notes:'Cancelled — superseded by NPD-2026-001.',
    comments:[],emails:[],
  },
];
