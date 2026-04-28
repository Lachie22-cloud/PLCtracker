export interface LifecycleStage {
  id: string;
  label: string;
  desc: string;
  color: string;
}

export interface LifecycleSku {
  matnr: string;
  desc: string;
  mtart: string;
  stage: string;
  health: number | null;
  plants: string[];
  target_date: string;
  days_in_stage: number;
  violations: number;
  last_change: string;
  pid: string;
  product: string;
  division: string;
  owner: string;
}

export interface ActivityRow {
  when: string;
  who: string;
  matnr: string;
  action: string;
  from: string | null;
  to: string | null;
  note: string;
}

export interface UploadRow {
  id: number;
  file: string;
  rows: number;
  accepted: number;
  errors: number;
  who: string;
  when: string;
  status: 'success' | 'partial' | 'error';
  error?: string;
}

export const LIFECYCLE_STAGES: LifecycleStage[] = [
  { id:'P0',label:'Pre-launch', desc:'Concept and spec',           color:'muted'   },
  { id:'A1',label:'Active',     desc:'In production / sale',       color:'ok'      },
  { id:'A2',label:'Mature',     desc:'Plateau, optimise margin',   color:'info'    },
  { id:'O1',label:'Phase-out',  desc:'Sell-through, no replenish', color:'warning' },
  { id:'O2',label:'Obsoletion', desc:'Block planning, drain stock', color:'warning' },
  { id:'O3',label:'Obsolete',   desc:'Closed, archived',           color:'critical'},
];

export const stageMeta = (id: string): LifecycleStage =>
  LIFECYCLE_STAGES.find(s => s.id === id) ?? LIFECYCLE_STAGES[0];

const LC_PRODUCTS_RAW = [
  { pid:'PR-BR-FRONT',name:'Front Brake assemblies',division:'54',owner:'L.Decker',
    skus:[
      {matnr:'MAT-000482',desc:'Brake assy. type B / front axle',mtart:'FERT',stage:'O2',health:78, plants:['1100','2100','3000'],target_date:'2026-06-15',days_in_stage:41, violations:2,last_change:'2026-04-28T07:12:04Z'},
      {matnr:'MAT-008420',desc:'Mount bracket, lower',            mtart:'FERT',stage:'A1',health:92, plants:['1100','3100'],       target_date:'—',         days_in_stage:184,violations:1,last_change:'2026-04-25T07:15:04Z'},
    ]},
  { pid:'PR-DRIVE',name:'Drive units',division:'54',owner:'L.Decker',
    skus:[
      {matnr:'MAT-002048',desc:'Drive unit, 48V',     mtart:'FERT',stage:'A2',health:88,plants:['1000','4000'],target_date:'—',days_in_stage:312,violations:2,last_change:'2026-04-28T07:12:11Z'},
      {matnr:'MAT-005220',desc:'Front cover, painted', mtart:'FERT',stage:'A1',health:95,plants:['1100','3000'],target_date:'—',days_in_stage:96, violations:1,last_change:'2026-04-26T07:14:09Z'},
    ]},
  { pid:'PR-RAW',name:'Raw materials',division:'55',owner:'S.Vogel',
    skus:[
      {matnr:'MAT-004061',desc:'Aluminium rod, 6082-T6',mtart:'ROH',stage:'A1',health:64,plants:['1000','2000'],target_date:'—',days_in_stage:502,violations:2,last_change:'2026-04-27T07:14:05Z'},
    ]},
  { pid:'PR-PACK',name:'Packaging (legacy)',division:'55',owner:'M.Heinrich',
    skus:[
      {matnr:'MAT-003412',desc:'Carton, brake assy. (legacy)',mtart:'VERP',stage:'O3',health:22,plants:['2000','2100'],target_date:'2026-04-30',days_in_stage:71,violations:2,last_change:'2026-04-27T07:14:02Z'},
    ]},
  { pid:'PR-SPARES',name:'Spare parts',division:'75',owner:'S.Vogel',
    skus:[
      {matnr:'MAT-002199',desc:'Replacement bearing kit',         mtart:'ERSA',stage:'A1',health:71,plants:['1100','3100'],target_date:'—',days_in_stage:218,violations:2,last_change:'2026-04-28T07:12:14Z'},
      {matnr:'MAT-009110',desc:'Service kit, brake (universal)',  mtart:'ERSA',stage:'A1',health:85,plants:['1000','2000'],target_date:'—',days_in_stage:130,violations:1,last_change:'2026-04-24T07:14:55Z'},
    ]},
  { pid:'PR-CONCEPTS',name:'Concept track',division:'54',owner:'Anya K.',
    skus:[
      {matnr:'MAT-018442',desc:'BR-front mk2 (concept)',    mtart:'FERT',stage:'P0',health:null,plants:[],target_date:'2026-08-01',days_in_stage:21,violations:0,last_change:'2026-04-22T11:00:00Z'},
      {matnr:'MAT-018501',desc:'Service-only kit (concept)',mtart:'ERSA',stage:'P0',health:null,plants:[],target_date:'2026-05-30',days_in_stage:27,violations:0,last_change:'2026-04-18T10:12:00Z'},
    ]},
  { pid:'PR-PHASEOUT',name:'Trading goods (phasing)',division:'75',owner:'M.Heinrich',
    skus:[
      {matnr:'MAT-006788',desc:'Sealant tube, 250 ml',      mtart:'HAWA',stage:'O1',health:58,plants:['1000','4000'],target_date:'2026-07-15',days_in_stage:33,violations:2,last_change:'2026-04-26T07:14:11Z'},
      {matnr:'MAT-007301',desc:'Brake disc, 320 mm (legacy)',mtart:'FERT',stage:'O1',health:51,plants:['1100','2100'],target_date:'2026-06-30',days_in_stage:52,violations:2,last_change:'2026-04-25T07:15:01Z'},
    ]},
];

export const LC_SKUS: LifecycleSku[] = LC_PRODUCTS_RAW.flatMap(p =>
  p.skus.map(s => ({ ...s, pid: p.pid, product: p.name, division: p.division, owner: p.owner }))
);

export const LC_PRODUCTS = LC_PRODUCTS_RAW.map(p => ({ pid: p.pid, name: p.name, division: p.division, owner: p.owner, skuCount: p.skus.length }));

export const LC_ACTIVITY: ActivityRow[] = [
  { when:'2026-04-28T08:14:00Z',who:'Lena Decker',matnr:'MAT-000482',action:'stage_change',from:'O1',to:'O2',note:'Drained stock at 2100; obsoletion ratified.'},
  { when:'2026-04-26T16:02:00Z',who:'M.Heinrich',  matnr:'MAT-003412',action:'stage_change',from:'O2',to:'O3',note:'All warehouse stock zero; closing out.'},
  { when:'2026-04-25T11:31:00Z',who:'Anya Krause', matnr:'MAT-018442',action:'create',      from:null,to:'P0',note:'Concept logged from NPD-2026-001.'},
  { when:'2026-04-24T09:18:00Z',who:'Lena Decker', matnr:'MAT-007301',action:'stage_change',from:'A2',to:'O1',note:'Volume below threshold for 90 days.'},
  { when:'2026-04-22T13:44:00Z',who:'S.Vogel',     matnr:'MAT-006788',action:'stage_change',from:'A2',to:'O1',note:'Supplier discontinuation.'},
];

export const LC_UPLOADS: UploadRow[] = [
  { id:18,file:'lifecycle-2026-04-28.csv', rows:11,accepted:11,errors:0,who:'Lena Decker',when:'2026-04-28T08:14:00Z',status:'success'},
  { id:17,file:'lifecycle-2026-04-22.xlsx',rows:7, accepted:6, errors:1,who:'Anya Krause',when:'2026-04-22T11:01:00Z',status:'partial',error:"Row 4: stage 'A3' not in vocabulary."},
  { id:16,file:'lifecycle-2026-04-15.csv', rows:22,accepted:22,errors:0,who:'M.Heinrich',  when:'2026-04-15T10:08:00Z',status:'success'},
  { id:15,file:'manual-bulk-update.csv',   rows:4, accepted:0, errors:4,who:'S.Vogel',     when:'2026-04-09T16:42:00Z',status:'error',  error:'Header row missing — expected matnr,stage,target_date.'},
];
