export type Region = 'DE' | 'CZ' | 'BE' | 'NL' | 'US';
export type PlantType = 'factory' | 'warehouse';

export interface Plant {
  code: string;
  name: string;
  type: PlantType;
  region: Region;
}

export interface MaterialType {
  code: string;
  label: string;
}

export interface FieldDef {
  name: string;
  label: string;
  severity_default: 'error' | 'warning' | 'info';
}

export type Severity = 'error' | 'warning' | 'info';

export interface Violation {
  id: number;
  matnr: string;
  werks: string;
  mtart: string;
  field: string;
  actual: string;
  expected: string;
  stage: string;
  note: string;
  detected: string;
  severity: Severity;
}

export interface Material {
  matnr: string;
  maktx: string;
  mtart: string;
  family: string;
  owner: string;
}

export interface Snapshot {
  id: string;
  run_id: number;
  started: string;
  source: string;
}

export interface MaterialChange {
  snapshot_id: string;
  werks: string;
  field: string;
  old: string;
  new: string;
  violated: boolean;
  rule: string | null;
}

export interface ExtractionRun {
  id: number;
  source: string;
  status: 'success' | 'error' | 'running';
  records: number;
  mara: number;
  marc: number;
  changes: number;
  violations_rebuilt: number;
  started: string;
  finished: string | null;
  duration_s: number;
  error: string | null;
  user: string;
}

export interface Rule {
  id: number;
  field: string;
  mtart: string | null;
  werks: string | null;
  stage: string | null;
  expected: string | null;
  allowed: string | null;
  severity: Severity;
  description: string;
  active_violations: number;
  specificity: number;
}

export interface SapState {
  last_run_at: string;
  last_run_id: number;
  last_run_status: string;
  failed_in_last_24h: boolean;
  scheduler: string;
  next_run_at: string;
}

export const PLANTS: Plant[] = [
  { code: '1000', name: 'Werk Walldorf',   type: 'factory',   region: 'DE' },
  { code: '1100', name: 'Werk Heidelberg', type: 'factory',   region: 'DE' },
  { code: '2000', name: 'Werk Brno',       type: 'factory',   region: 'CZ' },
  { code: '2100', name: 'DC Brno',         type: 'warehouse', region: 'CZ' },
  { code: '3000', name: 'DC Antwerp',      type: 'warehouse', region: 'BE' },
  { code: '3100', name: 'DC Rotterdam',    type: 'warehouse', region: 'NL' },
  { code: '4000', name: 'DC Memphis',      type: 'warehouse', region: 'US' },
];

export const MTART: MaterialType[] = [
  { code: 'FERT', label: 'Finished good' },
  { code: 'HALB', label: 'Semi-finished' },
  { code: 'ROH',  label: 'Raw material' },
  { code: 'VERP', label: 'Packaging' },
  { code: 'ERSA', label: 'Spare part' },
  { code: 'HAWA', label: 'Trading good' },
];

export const FIELDS: FieldDef[] = [
  { name: 'DISPR', label: 'MRP profile',            severity_default: 'error' },
  { name: 'BESKZ', label: 'Procurement type',       severity_default: 'error' },
  { name: 'DISPO', label: 'MRP controller',         severity_default: 'warning' },
  { name: 'MTVFP', label: 'Availability check',     severity_default: 'error' },
  { name: 'EKGRP', label: 'Purchasing group',       severity_default: 'warning' },
  { name: 'DISMM', label: 'MRP type',               severity_default: 'error' },
  { name: 'EISBE', label: 'Safety stock',           severity_default: 'info' },
  { name: 'MMSTA', label: 'Plant-spec. material status', severity_default: 'error' },
];

const RAW_VIOLATIONS: Omit<Violation, 'id'>[] = [
  { matnr:'MAT-000482',werks:'2100',mtart:'FERT',field:'DISPR', actual:'ZF03',expected:'NOPL',   stage:'O2',note:'Plant-spec. status is O2 but MRP profile is still active.',detected:'2026-04-28T07:12:04Z',severity:'error'},
  { matnr:'MAT-000482',werks:'3000',mtart:'FERT',field:'BESKZ', actual:'F',  expected:'E',       stage:'A1',note:"Warehouse must use 'E' (in-house) when factory is 1100.",detected:'2026-04-28T07:12:04Z',severity:'error'},
  { matnr:'MAT-001137',werks:'1000',mtart:'HALB',field:'MTVFP', actual:'01', expected:'02',      stage:'A1',note:'Availability check must align with finished-good rule.',detected:'2026-04-28T07:12:08Z',severity:'error'},
  { matnr:'MAT-001137',werks:'2000',mtart:'HALB',field:'DISPO', actual:'P11',expected:'P10|P12', stage:'A1',note:'MRP controller out of allowed CZ pool.',detected:'2026-04-28T07:12:08Z',severity:'warning'},
  { matnr:'MAT-002048',werks:'1000',mtart:'FERT',field:'DISMM', actual:'VB', expected:'PD',      stage:'A1',note:"MRP type 'VB' not approved for finished goods at 1000.",detected:'2026-04-28T07:12:11Z',severity:'error'},
  { matnr:'MAT-002048',werks:'4000',mtart:'FERT',field:'MMSTA', actual:'A1', expected:'O2',      stage:'O2',note:'Family at obsoletion but warehouse still A1.',detected:'2026-04-28T07:12:11Z',severity:'warning'},
  { matnr:'MAT-002199',werks:'1100',mtart:'ERSA',field:'DISPR', actual:'',   expected:'ZSPR',    stage:'A1',note:'Spare parts require ZSPR profile (missing).',detected:'2026-04-28T07:12:14Z',severity:'error'},
  { matnr:'MAT-002199',werks:'3100',mtart:'ERSA',field:'EKGRP', actual:'P30',expected:'P40',     stage:'A1',note:'Purchasing group mismatch with corp policy.',detected:'2026-04-28T07:12:14Z',severity:'warning'},
  { matnr:'MAT-003412',werks:'2000',mtart:'VERP',field:'DISPR', actual:'ZA02',expected:'OBSO',   stage:'O3',note:'Material is obsolete; profile should be OBSO.',detected:'2026-04-27T07:14:02Z',severity:'error'},
  { matnr:'MAT-003412',werks:'2100',mtart:'VERP',field:'MMSTA', actual:'A1', expected:'O3',      stage:'O3',note:'Status flag stale on warehouse plant.',detected:'2026-04-27T07:14:02Z',severity:'error'},
  { matnr:'MAT-004061',werks:'1000',mtart:'ROH', field:'BESKZ', actual:'X',  expected:'F',       stage:'A1',note:'Raw materials must be externally procured.',detected:'2026-04-27T07:14:02Z',severity:'error'},
  { matnr:'MAT-004061',werks:'2000',mtart:'ROH', field:'EISBE', actual:'0',  expected:'>= 50',   stage:'A1',note:'Safety stock below corporate minimum.',detected:'2026-04-27T07:14:05Z',severity:'info'},
  { matnr:'MAT-005220',werks:'1100',mtart:'FERT',field:'DISPO', actual:'P02',expected:'P01|P02|P03',stage:'A1',note:'OK — sample of warning rule edge case.',detected:'2026-04-26T07:14:09Z',severity:'warning'},
  { matnr:'MAT-005220',werks:'3000',mtart:'FERT',field:'DISPR', actual:'ZF01',expected:'ZF03',   stage:'A1',note:'Wrong MRP profile for warehouse routing.',detected:'2026-04-26T07:14:09Z',severity:'error'},
  { matnr:'MAT-006788',werks:'4000',mtart:'HAWA',field:'MTVFP', actual:'KP', expected:'02',      stage:'A1',note:'Trading goods must use ATP scope 02.',detected:'2026-04-26T07:14:11Z',severity:'error'},
  { matnr:'MAT-006788',werks:'1000',mtart:'HAWA',field:'DISPR', actual:'',   expected:'ZHAW',    stage:'A1',note:'Required profile missing for HAWA at 1000.',detected:'2026-04-26T07:14:11Z',severity:'error'},
  { matnr:'MAT-007301',werks:'2100',mtart:'FERT',field:'DISMM', actual:'PD', expected:'ND',      stage:'O1',note:'Stage O1 requires no-demand planning.',detected:'2026-04-25T07:15:01Z',severity:'warning'},
  { matnr:'MAT-007301',werks:'1100',mtart:'FERT',field:'EKGRP', actual:'P10',expected:'P50',     stage:'O1',note:'Phase-out group not assigned.',detected:'2026-04-25T07:15:01Z',severity:'info'},
  { matnr:'MAT-008420',werks:'3100',mtart:'FERT',field:'BESKZ', actual:'F',  expected:'E',       stage:'A1',note:'Should be in-house — factory is 1100.',detected:'2026-04-25T07:15:01Z',severity:'error'},
  { matnr:'MAT-008420',werks:'1100',mtart:'FERT',field:'DISPR', actual:'ZF02',expected:'ZF03',   stage:'A1',note:'Profile drifted from family policy.',detected:'2026-04-25T07:15:04Z',severity:'warning'},
  { matnr:'MAT-009110',werks:'1000',mtart:'ERSA',field:'MTVFP', actual:'01', expected:'02',      stage:'A1',note:'Spares ATP scope incorrect.',detected:'2026-04-24T07:14:55Z',severity:'error'},
  { matnr:'MAT-009110',werks:'2000',mtart:'ERSA',field:'DISPR', actual:'ZSPR',expected:'ZSPR',   stage:'A1',note:'Resolved (kept for snapshot only).',detected:'2026-04-24T07:14:55Z',severity:'info'},
];

export const VIOLATIONS: Violation[] = RAW_VIOLATIONS.map((v, i) => ({ ...v, id: i + 1 }));

export const MATERIALS: Material[] = [
  { matnr:'MAT-000482',maktx:'Brake assy. type B / front axle',mtart:'FERT',family:'BR-Front',owner:'L.Decker'},
  { matnr:'MAT-001137',maktx:'Composite frame – inner panel',   mtart:'HALB',family:'FR-Inner',owner:'M.Heinrich'},
  { matnr:'MAT-002048',maktx:'Drive unit, 48V',                 mtart:'FERT',family:'DU-48V',  owner:'L.Decker'},
  { matnr:'MAT-002199',maktx:'Replacement bearing kit',         mtart:'ERSA',family:'BR-Front',owner:'S.Vogel'},
  { matnr:'MAT-003412',maktx:'Carton, brake assy. (legacy)',    mtart:'VERP',family:'BR-Front',owner:'M.Heinrich'},
  { matnr:'MAT-004061',maktx:'Aluminium rod, 6082-T6',          mtart:'ROH', family:'RM-Al',   owner:'S.Vogel'},
  { matnr:'MAT-005220',maktx:'Front cover, painted',            mtart:'FERT',family:'FR-Cover',owner:'L.Decker'},
  { matnr:'MAT-006788',maktx:'Sealant tube, 250 ml',            mtart:'HAWA',family:'AC-Seal', owner:'M.Heinrich'},
  { matnr:'MAT-007301',maktx:'Brake disc, 320 mm (legacy)',     mtart:'FERT',family:'BR-Disc', owner:'L.Decker'},
  { matnr:'MAT-008420',maktx:'Mount bracket, lower',            mtart:'FERT',family:'BR-Front',owner:'S.Vogel'},
  { matnr:'MAT-009110',maktx:'Service kit, brake (universal)',  mtart:'ERSA',family:'BR-Disc', owner:'M.Heinrich'},
];

export const SNAPSHOTS: Snapshot[] = [
  { id:'snap-2026-04-28',run_id:142,started:'2026-04-28T07:12:00Z',source:'SAP OData'},
  { id:'snap-2026-04-27',run_id:141,started:'2026-04-27T07:14:00Z',source:'SAP OData'},
  { id:'snap-2026-04-26',run_id:140,started:'2026-04-26T07:14:00Z',source:'SAP OData'},
  { id:'snap-2026-04-25',run_id:139,started:'2026-04-25T07:15:00Z',source:'SAP OData'},
  { id:'snap-2026-04-24',run_id:138,started:'2026-04-24T07:14:00Z',source:'SAP OData'},
  { id:'snap-2026-04-23',run_id:137,started:'2026-04-23T07:14:00Z',source:'SAP OData'},
];

export const MATERIAL_CHANGES: Record<string, MaterialChange[]> = {
  'MAT-000482': [
    {snapshot_id:'snap-2026-04-28',werks:'2100',field:'DISPR',old:'ZA02',new:'ZF03',violated:true, rule:'DISPR.O2.NOPL'},
    {snapshot_id:'snap-2026-04-28',werks:'3000',field:'BESKZ',old:'E',   new:'F',   violated:true, rule:'BESKZ.warehouse.E'},
    {snapshot_id:'snap-2026-04-27',werks:'2100',field:'DISPO', old:'P10', new:'P12', violated:false,rule:null},
    {snapshot_id:'snap-2026-04-25',werks:'1100',field:'EISBE', old:'40',  new:'60',  violated:false,rule:null},
    {snapshot_id:'snap-2026-04-24',werks:'1100',field:'MMSTA', old:'A1',  new:'O1',  violated:false,rule:null},
    {snapshot_id:'snap-2026-04-23',werks:'2100',field:'DISPR', old:'ZF03',new:'ZA02',violated:false,rule:null},
  ],
  'MAT-002048': [
    {snapshot_id:'snap-2026-04-28',werks:'1000',field:'DISMM',old:'PD', new:'VB', violated:true, rule:'DISMM.FERT.PD'},
    {snapshot_id:'snap-2026-04-28',werks:'4000',field:'MMSTA',old:'O1', new:'A1', violated:true, rule:'MMSTA.family-align'},
    {snapshot_id:'snap-2026-04-26',werks:'1000',field:'EKGRP',old:'P10',new:'P11',violated:false,rule:null},
  ],
  'MAT-003412': [
    {snapshot_id:'snap-2026-04-27',werks:'2000',field:'DISPR',old:'OBSO',new:'ZA02',violated:true, rule:'DISPR.O3.OBSO'},
    {snapshot_id:'snap-2026-04-27',werks:'2100',field:'MMSTA',old:'O3', new:'A1',  violated:true, rule:'MMSTA.family-align'},
  ],
};

export const RUNS: ExtractionRun[] = [
  {id:142,source:'SAP OData',    status:'success',records:18420,mara:11240,marc:18420,changes:87, violations_rebuilt:142,started:'2026-04-28T07:12:00Z',finished:'2026-04-28T07:14:38Z',duration_s:158,error:null,user:'scheduler'},
  {id:141,source:'SAP OData',    status:'success',records:18412,mara:11238,marc:18412,changes:64, violations_rebuilt:138,started:'2026-04-27T07:14:00Z',finished:'2026-04-27T07:16:31Z',duration_s:151,error:null,user:'scheduler'},
  {id:140,source:'SAP OData',    status:'success',records:18404,mara:11236,marc:18404,changes:32, violations_rebuilt:134,started:'2026-04-26T07:14:00Z',finished:'2026-04-26T07:16:11Z',duration_s:131,error:null,user:'scheduler'},
  {id:139,source:'SAP OData',    status:'error',  records:0,    mara:0,    marc:0,    changes:0,  violations_rebuilt:0,  started:'2026-04-25T07:15:00Z',finished:'2026-04-25T07:15:42Z',duration_s:42, error:'OData /sap/opu/odata/sap/MM_MATERIAL_SRV/A_Product timeout after 30s; 504 Gateway Timeout from SAP gateway sapprd-eu1:8443.',user:'scheduler'},
  {id:138,source:'Manual upload',status:'success',records:18380,mara:11230,marc:18380,changes:12, violations_rebuilt:130,started:'2026-04-24T07:14:00Z',finished:'2026-04-24T07:15:50Z',duration_s:110,error:null,user:'l.decker@plct.io'},
  {id:137,source:'SAP OData',    status:'success',records:18376,mara:11228,marc:18376,changes:41, violations_rebuilt:128,started:'2026-04-23T07:14:00Z',finished:'2026-04-23T07:16:02Z',duration_s:122,error:null,user:'scheduler'},
  {id:136,source:'SAP OData',    status:'success',records:18372,mara:11227,marc:18372,changes:28, violations_rebuilt:124,started:'2026-04-22T07:14:00Z',finished:'2026-04-22T07:15:44Z',duration_s:104,error:null,user:'scheduler'},
];

export const RULES: Rule[] = [
  {id:1, field:'DISPR',mtart:'FERT',werks:null,  stage:'O2',expected:'NOPL',allowed:null,    severity:'error',  description:"Obsoleting finished goods must be 'NOPL'.",                                     active_violations:7, specificity:0.72},
  {id:2, field:'DISPR',mtart:'FERT',werks:null,  stage:'O3',expected:'OBSO',allowed:null,    severity:'error',  description:"Obsolete finished goods must be 'OBSO'.",                                     active_violations:4, specificity:0.72},
  {id:3, field:'DISPR',mtart:'ERSA',werks:null,  stage:null,expected:'ZSPR',allowed:null,    severity:'error',  description:'Spare parts always use ZSPR.',                                                 active_violations:3, specificity:0.55},
  {id:4, field:'DISPR',mtart:'HAWA',werks:'1000',stage:null,expected:'ZHAW',allowed:null,    severity:'error',  description:'HAWA at 1000 must be ZHAW.',                                                   active_violations:2, specificity:0.91},
  {id:5, field:'BESKZ',mtart:null,  werks:'3000',stage:null,expected:'E',   allowed:'E',     severity:'error',  description:'Warehouses must always be in-house procurement.',                              active_violations:3, specificity:0.62},
  {id:6, field:'BESKZ',mtart:'ROH', werks:null,  stage:null,expected:'F',   allowed:'F',     severity:'error',  description:'Raw materials must be externally procured.',                                   active_violations:1, specificity:0.55},
  {id:7, field:'DISPO',mtart:null,  werks:'2000',stage:null,expected:null,  allowed:'P10|P12',severity:'warning',description:'CZ MRP controllers limited to P10 and P12.',                                active_violations:2, specificity:0.55},
  {id:8, field:'MTVFP',mtart:'FERT',werks:null,  stage:'A1',expected:'02',  allowed:null,    severity:'error',  description:'Active finished goods use ATP scope 02.',                                      active_violations:2, specificity:0.72},
  {id:9, field:'MTVFP',mtart:'ERSA',werks:null,  stage:null,expected:'02',  allowed:null,    severity:'error',  description:'Spare parts use ATP scope 02.',                                               active_violations:1, specificity:0.55},
  {id:10,field:'DISMM',mtart:'FERT',werks:null,  stage:'A1',expected:'PD',  allowed:null,    severity:'error',  description:'Active finished goods plan with PD.',                                          active_violations:1, specificity:0.72},
  {id:11,field:'DISMM',mtart:null,  werks:null,  stage:'O1',expected:'ND',  allowed:null,    severity:'warning',description:'Phase-out stage uses ND (no demand).',                                        active_violations:1, specificity:0.45},
  {id:12,field:'MMSTA',mtart:null,  werks:null,  stage:null,expected:null,  allowed:null,    severity:'warning',description:'Family-status alignment: factory ↔ warehouse must match.',                   active_violations:4, specificity:0.20},
  {id:13,field:'EKGRP',mtart:'ERSA',werks:null,  stage:null,expected:'P40', allowed:null,    severity:'warning',description:'Spare parts purchasing group is P40.',                                        active_violations:1, specificity:0.55},
  {id:14,field:'EKGRP',mtart:null,  werks:null,  stage:'O1',expected:'P50', allowed:null,    severity:'info',   description:'Phase-out items go to P50 (legacy buy-out).',                                 active_violations:1, specificity:0.45},
  {id:15,field:'EISBE',mtart:'ROH', werks:null,  stage:null,expected:null,  allowed:'>= 50', severity:'info',   description:'Raw materials must keep >= 50 units safety stock.',                           active_violations:1, specificity:0.55},
];

export const SAP_STATE: SapState = {
  last_run_at: '2026-04-28T07:14:38Z',
  last_run_id: 142,
  last_run_status: 'success',
  failed_in_last_24h: false,
  scheduler: 'Daily 07:12 UTC',
  next_run_at: '2026-04-29T07:12:00Z',
};
