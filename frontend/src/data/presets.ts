export interface Division {
  code: string;
  label: string;
  color: 'violet' | 'amber' | 'blue';
}

export interface NpdPlant {
  code: string;
  name: string;
}

export interface FieldKbEntry {
  code: string;
  label: string;
  table: string;
  what: string;
  why: string;
  example: string;
  allowed_examples?: string[];
}

export interface PresetField {
  field: string;
  label: string;
  allowed: string[];
}

export interface Preset {
  id: string;
  name: string;
  description: string;
  plants: string[];
  display_order: number;
  critical: PresetField[];
  guidance: PresetField[];
}

export const DIVISIONS: Division[] = [
  { code: '54', label: 'Refinish',            color: 'violet' },
  { code: '55', label: 'Protective Coatings', color: 'amber' },
  { code: '75', label: 'Avista',              color: 'blue' },
];

export const NPD_PLANTS: NpdPlant[] = [
  { code: 'QF00', name: 'Queensferry Factory' },
  { code: 'QF10', name: 'Queensferry Bulk Store' },
  { code: 'BT00', name: 'Birtley Factory' },
  { code: 'DC10', name: 'Antwerp DC' },
  { code: 'DC20', name: 'Rotterdam DC' },
  { code: 'DC30', name: 'Memphis DC' },
];

export const FIELD_KB: Record<string, FieldKbEntry> = {
  DISMM: {
    code:'DISMM',label:'MRP Type',table:'MARC',
    what:'Controls which materials-requirements planning procedure is used at this plant. Drives whether SAP plans by reorder point, forecast, deterministic MRP, or no planning at all.',
    why:"Wrong MRP type silently breaks demand calculation. A finished good marked 'VB' (reorder point) won't react to forecast changes; a raw material on 'PD' will create planned orders the planner can't fulfill.",
    example:'PD — deterministic MRP (most finished goods); VB — reorder point; ND — no planning.',
    allowed_examples:['PD','VB','MK','ND'],
  },
  DISPR: {
    code:'DISPR',label:'MRP Profile',table:'MARC',
    what:'Reusable bundle of MRP defaults applied at the plant. A profile sets MRP type, lot-sizing, safety stock and rounding values in one go.',
    why:'Profiles encode plant-specific recipes for each material type. A finished good with the wrong profile inherits incorrect lot-sizes, planning horizons and safety stock — root cause of phantom shortages.',
    example:'ZF03 — finished goods at factory; ZHAW — trading goods; OBSO — obsolete.',
    allowed_examples:['ZF03','ZHAW','ZSPR','OBSO'],
  },
  BESKZ: {
    code:'BESKZ',label:'Procurement Type',table:'MARC',
    what:"Tells SAP whether the material is made in-house (E), externally procured (F), or both (X) at this plant.",
    why:"If a raw material is set to 'E' SAP will try to create planned production orders for it — a hard error that blocks the planning run for everything below it.",
    example:'F — externally procured; E — in-house production; X — both.',
    allowed_examples:['E','F','X'],
  },
  DISPO: {
    code:'DISPO',label:'MRP Controller',table:'MARC',
    what:'Person or planning group responsible for this material at this plant. Used to filter MRP exception monitors and route orders.',
    why:'Wrong controller means exceptions land on the wrong desk. Often masked for months until a supervisor reviews coverage.',
    example:'P10 — Walldorf finished goods; P40 — Brno semi-finished.',
    allowed_examples:['P10','P11','P12','P40'],
  },
  MTVFP: {
    code:'MTVFP',label:'Availability Check',table:'MARC',
    what:'Defines how SAP performs ATP (available-to-promise) checks for this material at this plant.',
    why:'Drives every confirmation customers see. The wrong scope can make stock invisible to sales orders, or worse, double-confirm against the same physical stock.',
    example:'02 — individual requirements; KP — no check.',
    allowed_examples:['01','02','KP'],
  },
  MMSTA: {
    code:'MMSTA',label:'Plant-spec. Material Status',table:'MARC',
    what:'Restricts what can happen to a material at this plant — block orders, deliveries, MRP, etc. Status codes are configured per company.',
    why:'Critical for end-of-life. A material flagged O2 (obsoletion) at the factory but A1 (active) at the warehouse causes silent over-production.',
    example:'A1 — active; O2 — phasing out; O3 — obsolete.',
    allowed_examples:['A1','O2','O3'],
  },
  EKGRP: {
    code:'EKGRP',label:'Purchasing Group',table:'MARC',
    what:'Buyer or buyer-group responsible for procurement of the material at this plant.',
    why:'Drives PO routing and approval workflows. Wrong group → POs sit waiting on the wrong approver.',
    example:'P30 — Indirect; P40 — Raw materials EU.',
    allowed_examples:['P30','P40'],
  },
  EISBE: {
    code:'EISBE',label:'Safety Stock',table:'MARC',
    what:'Quantity of stock SAP must keep on hand to cover supply variability before triggering a replenishment.',
    why:'Below-policy safety stock causes service-level misses; above-policy ties up working capital.',
    example:'Numeric — units of base UoM. Policy minimum 50 EA for raw materials.',
    allowed_examples:['>= 50'],
  },
};

export const fieldKb = (code: string): FieldKbEntry =>
  FIELD_KB[code] ?? { code, label: code, table: '—', what: 'Field documentation not yet imported.', why: 'Add an entry to the field knowledge base.', example: '—' };

export const PRESETS: Preset[] = [
  {
    id:'bulk',name:'Bulk',
    description:'Bulk paint and coating intermediates produced and stored at factories.',
    plants:['QF00','BT00'],display_order:1,
    critical:[
      {field:'DISMM',label:'MRP Type',         allowed:['PD','VB']},
      {field:'BESKZ',label:'Procurement Type', allowed:['E']},
      {field:'MTVFP',label:'Availability Check',allowed:['02']},
    ],
    guidance:[
      {field:'DISPO',label:'MRP Controller', allowed:['P10','P11','P12']},
      {field:'EISBE',label:'Safety Stock',   allowed:['>= 50']},
    ],
  },
  {
    id:'packaging',name:'Packaging',
    description:'Cans, lids, tubes, labels, cartons and shrink-wrap consumed at factories.',
    plants:['QF00','BT00'],display_order:2,
    critical:[
      {field:'BESKZ',label:'Procurement Type',allowed:['F']},
      {field:'MMSTA',label:'Plant Status',    allowed:['A1']},
    ],
    guidance:[
      {field:'EKGRP',label:'Purchasing Group',allowed:['P30','P40']},
    ],
  },
  {
    id:'fg_factory',name:'Finished Good at Factory',
    description:'Finished SKUs filled, labelled and packed at the producing factory.',
    plants:['QF00','BT00'],display_order:3,
    critical:[
      {field:'DISMM',label:'MRP Type',          allowed:['PD','VB','MK']},
      {field:'DISPR',label:'MRP Profile',       allowed:['ZF03']},
      {field:'BESKZ',label:'Procurement Type',  allowed:['E']},
      {field:'MTVFP',label:'Availability Check',allowed:['02']},
    ],
    guidance:[
      {field:'DISPO',label:'MRP Controller',  allowed:['P10','P11']},
      {field:'EKGRP',label:'Purchasing Group',allowed:['P30']},
      {field:'EISBE',label:'Safety Stock',    allowed:['>= 50']},
    ],
  },
  {
    id:'mto_factory',name:'Make to Order at Factory',
    description:'Customer-specific finished SKUs produced to order at the factory.',
    plants:['QF00','BT00'],display_order:4,
    critical:[
      {field:'DISMM',label:'MRP Type',        allowed:['MK']},
      {field:'DISPR',label:'MRP Profile',     allowed:['ZMTO']},
      {field:'BESKZ',label:'Procurement Type',allowed:['E']},
    ],
    guidance:[
      {field:'DISPO',label:'MRP Controller',allowed:['P12']},
    ],
  },
  {
    id:'intermediate',name:'Intermediate',
    description:'Semi-finished components consumed within the factory before becoming FG or Bulk.',
    plants:['QF00','BT00'],display_order:5,
    critical:[
      {field:'BESKZ',label:'Procurement Type', allowed:['E']},
      {field:'MTVFP',label:'Availability Check',allowed:['02']},
    ],
    guidance:[
      {field:'DISPO',label:'MRP Controller',allowed:['P10','P12']},
    ],
  },
  {
    id:'fg_warehouse',name:'Finished Good at Warehouse',
    description:'Finished SKUs replenished from a producing factory and held for distribution.',
    plants:['DC10','DC20','DC30'],display_order:6,
    critical:[
      {field:'DISMM',label:'MRP Type',          allowed:['VB','PD']},
      {field:'DISPR',label:'MRP Profile',       allowed:['ZFGW']},
      {field:'BESKZ',label:'Procurement Type',  allowed:['F']},
      {field:'MTVFP',label:'Availability Check',allowed:['02']},
    ],
    guidance:[
      {field:'EISBE',label:'Safety Stock',    allowed:['>= 100']},
      {field:'EKGRP',label:'Purchasing Group',allowed:['P40']},
    ],
  },
  {
    id:'mto_warehouse',name:'Make to Order at Warehouse',
    description:'MTO finished SKUs picked at warehouse but never stocked. Pass-through plant view.',
    plants:['DC10','DC20'],display_order:7,
    critical:[
      {field:'DISMM',label:'MRP Type',   allowed:['ND']},
      {field:'MMSTA',label:'Plant Status',allowed:['A1']},
    ],
    guidance:[],
  },
];
