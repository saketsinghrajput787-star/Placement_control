import React, { useState, useEffect, Component, ErrorInfo, ReactNode } from 'react';
import { apiClient } from '../../api/client';
import { DocumentItem, DocumentUploadResponse } from '../../types';
import { useOperations } from '../../store/operationsStore';

interface ErrorBoundaryProps {
  children: ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

class DataImportErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  public state: ErrorBoundaryState = {
    hasError: false,
    error: null
  };

  public static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('DataImportCenter error caught:', error, errorInfo);
  }

  public render() {
    if (this.state.hasError) {
      return (
        <div className="p-8 bg-rose-50 border border-rose-200 rounded-3xl space-y-4 text-xs font-bold text-rose-900">
          <h3 className="text-lg font-black text-rose-950">⚠️ Render Error in Data Import Center</h3>
          <p>An unexpected error occurred while rendering document preview:</p>
          <pre className="p-4 bg-white rounded-xl border border-rose-300 font-mono text-[11px] overflow-x-auto text-rose-800">
            {this.state.error?.toString()}
          </pre>
          <button
            onClick={() => this.setState({ hasError: false, error: null })}
            className="px-4 py-2 bg-rose-800 text-white rounded-xl hover:bg-rose-900 transition-colors"
          >
            [ Reset Workspace ]
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

const CATEGORIES = [
  "Auto-Detect (Recommended)",
  "Students",
  "Companies",
  "Shortlists",
  "Rooms",
  "Panels",
  "Company Availability",
  "Student Availability",
  "Interview Requirements",
  "Placement Rules",
  "Other"
];

const formatErrorMessage = (err: any, fallback: string): string => {
  if (!err) return fallback;
  const detail = err.response?.data?.detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    return detail.map((d: any) => typeof d === 'string' ? d : (d.msg || d.message || JSON.stringify(d))).join('; ');
  }
  if (typeof detail === 'object' && detail !== null) {
    return detail.message || detail.msg || JSON.stringify(detail);
  }
  return err.message || fallback;
};

const DataImportCenterContent: React.FC = () => {
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [isUploading, setIsUploading] = useState<boolean>(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [category, setCategory] = useState<string>('Auto-Detect (Recommended)');
  const [uploadResult, setUploadResult] = useState<DocumentUploadResponse | null>(null);
  const [previewDoc, setPreviewDoc] = useState<any>(null);
  const [isImporting, setIsImporting] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [isClearing, setIsClearing] = useState<boolean>(false);
  const [isSyncing, setIsSyncing] = useState<boolean>(false);

  const { loadDashboardData } = useOperations();

  const fetchDocuments = async () => {
    try {
      const res = await apiClient.get('/documents');
      setDocuments(Array.isArray(res.data) ? res.data : []);
    } catch (err) {
      console.error('Failed to fetch documents', err);
      setDocuments([]);
    }
  };

  useEffect(() => {
    fetchDocuments();
  }, []);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setSelectedFile(file);
      setUploadResult(null);
      setPreviewDoc(null);
      setError(null);

      const fname = file.name.toLowerCase().replace(/_/g, ' ');
      if (fname.includes('company availability') || fname.includes('comp avail')) {
        setCategory('Company Availability');
      } else if (fname.includes('student availability') || fname.includes('stud avail')) {
        setCategory('Student Availability');
      } else if (fname.includes('interview requirement') || fname.includes('requirement')) {
        setCategory('Interview Requirements');
      } else if (fname.includes('placement rule') || fname.includes('rule')) {
        setCategory('Placement Rules');
      } else if (fname.includes('shortlist')) {
        setCategory('Shortlists');
      } else if (fname.includes('room')) {
        setCategory('Rooms');
      } else if (fname.includes('panel')) {
        setCategory('Panels');
      } else if (fname.includes('company') || fname.includes('companies')) {
        setCategory('Companies');
      } else if (fname.includes('student') || fname.includes('students')) {
        setCategory('Students');
      } else {
        setCategory('Auto-Detect (Recommended)');
      }
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) return;
    setIsUploading(true);
    setError(null);
    setSuccessMsg(null);

    const formData = new FormData();
    formData.append('file', selectedFile);
    if (category && category !== 'Auto-Detect (Recommended)') {
      formData.append('document_type', category);
    }
    formData.append('uploaded_by', 'Coordinator');

    try {
      const res = await apiClient.post('/documents/upload', formData);
      setUploadResult(res.data);
      if (res.data?.document_type) {
        setCategory(res.data.document_type);
      }
      fetchDocuments();
    } catch (err: any) {
      console.error('Upload failed', err);
      setError(formatErrorMessage(err, 'Failed to upload document'));
    } finally {
      setIsUploading(false);
    }
  };

  const [importMode, setImportMode] = useState<string>('REPLACE');

  const handleConfirmImport = async (docId: string) => {
    setIsImporting(true);
    setError(null);
    try {
      const res = await apiClient.post(`/documents/${docId}/import?import_mode=${importMode}`);
      setSuccessMsg(`Successfully imported document! Mode: ${importMode}.`);
      setUploadResult(null);
      setPreviewDoc(null);
      fetchDocuments();
      await loadDashboardData();
    } catch (err: any) {
      console.error('Import failed', err);
      setError(formatErrorMessage(err, 'Failed to import dataset'));
    } finally {
      setIsImporting(false);
    }
  };

  const handleViewPreview = async (docId: string) => {
    try {
      const res = await apiClient.get(`/documents/${docId}`);
      setPreviewDoc(res.data);
    } catch (err: any) {
      console.error('Failed to load doc preview', err);
      setError(formatErrorMessage(err, 'Failed to load preview'));
    }
  };

  const handleDownloadErrorReport = (docId: string, filename: string) => {
    window.open(`${apiClient.defaults.baseURL}/documents/${docId}/error-report`, '_blank');
  };

  const handleClearAllData = async () => {
    if (!window.confirm('Are you sure you want to purge all imported datasets and reset all system entities to 0?')) {
      return;
    }
    setIsClearing(true);
    setError(null);
    setSuccessMsg(null);
    try {
      await apiClient.post('/documents/clear-all');
      setSuccessMsg('All system data, uploaded documents, and entity records have been cleared successfully.');
      setUploadResult(null);
      setPreviewDoc(null);
      setSelectedFile(null);
      fetchDocuments();
      await loadDashboardData();
    } catch (err: any) {
      console.error('Failed to clear data', err);
      setError(formatErrorMessage(err, 'Failed to clear system data'));
    } finally {
      setIsClearing(false);
    }
  };

  const handleSyncAllData = async () => {
    setIsSyncing(true);
    setError(null);
    setSuccessMsg(null);
    try {
      const res = await apiClient.post('/documents/sync-all');
      setSuccessMsg('System data updated & synchronized! Applied latest imported datasets across all 3 portals.');
      fetchDocuments();
      await loadDashboardData();
    } catch (err: any) {
      console.error('Failed to sync data', err);
      setError(formatErrorMessage(err, 'Failed to update system data'));
    } finally {
      setIsSyncing(false);
    }
  };

  const previewCols = Array.isArray(uploadResult?.columns) ? uploadResult.columns.slice(0, 6) : [];
  const previewRows = Array.isArray(uploadResult?.preview) ? uploadResult.preview : [];

  return (
    <div className="space-y-6">
      
      {/* Header Banner */}
      <div className="p-6 rounded-3xl bg-sand-100 border border-sand-200 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
          <span className="text-xs font-bold uppercase tracking-wider text-forest-700">Central Operating System</span>
          <h2 className="text-2xl font-black text-sand-900 mt-1">DATA IMPORT CENTER</h2>
          <p className="text-xs text-sand-600 mt-1">
            Ingest, validate, version, and synchronize college placement datasets across all 3 portals.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          <button
            onClick={handleClearAllData}
            disabled={isClearing || isSyncing}
            className="px-4 py-2.5 rounded-xl text-xs font-bold bg-rose-50 text-rose-800 border border-rose-300 hover:bg-rose-100 transition-colors shadow-sm disabled:opacity-50 flex items-center gap-1.5"
          >
            <span>{isClearing ? 'Clearing Data...' : '🗑️ Clear All Data'}</span>
          </button>

          <button
            onClick={handleSyncAllData}
            disabled={isSyncing || isClearing}
            className="px-4 py-2.5 rounded-xl text-xs font-bold bg-emerald-700 text-white hover:bg-emerald-800 transition-colors shadow-sm disabled:opacity-50 flex items-center gap-1.5"
          >
            <span>{isSyncing ? 'Updating Data...' : '🔄 Update System Data'}</span>
          </button>

          <label className="cursor-pointer px-5 py-2.5 rounded-xl text-xs font-bold bg-forest-800 text-white hover:bg-forest-900 transition-colors shadow-md flex items-center gap-2">
            <span>[ + Upload Document ]</span>
            <input
              type="file"
              accept=".csv,.xlsx,.xls,.pdf,.docx"
              onChange={handleFileSelect}
              className="hidden"
            />
          </label>
        </div>
      </div>

      {successMsg && (
        <div className="p-4 rounded-2xl bg-emerald-50 border border-emerald-200 text-emerald-900 text-xs font-bold flex justify-between items-center">
          <span>✓ {successMsg}</span>
          <button onClick={() => setSuccessMsg(null)} className="text-emerald-700 font-black">✕</button>
        </div>
      )}

      {error && (
        <div className="p-4 rounded-2xl bg-rose-50 border border-rose-200 text-rose-900 text-xs font-bold flex justify-between items-center">
          <span>⚠️ {typeof error === 'string' ? error : JSON.stringify(error)}</span>
          <button onClick={() => setError(null)} className="text-rose-700 font-black">✕</button>
        </div>
      )}

      {/* Upload & Validation Workspace */}
      {selectedFile && (
        <div className="p-6 rounded-3xl bg-white border border-sand-300 shadow-xl space-y-4 animate-in fade-in duration-150">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-black text-sand-900 flex items-center gap-2">
              <span>Selected Document:</span>
              <span className="text-forest-800 font-mono">{selectedFile.name}</span>
            </h3>
            <button onClick={() => setSelectedFile(null)} className="text-xs text-sand-400 hover:text-sand-700">Cancel</button>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-bold text-sand-800 mb-1.5">Document Category</label>
              <select
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                className="w-full px-3.5 py-2.5 rounded-xl border border-sand-300 text-xs font-bold text-sand-900 bg-white focus:outline-none focus:ring-2 focus:ring-forest-600"
              >
                {CATEGORIES.map(c => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            </div>

            <div className="flex items-end">
              <button
                onClick={handleUpload}
                disabled={isUploading}
                className="w-full py-2.5 rounded-xl text-xs font-bold bg-forest-800 text-white hover:bg-forest-900 transition-colors shadow-sm disabled:opacity-50"
              >
                {isUploading ? 'Validating & Uploading...' : 'Validate Document'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Upload Validation Preview Box */}
      {uploadResult && (
        <div className="p-6 rounded-3xl bg-white border border-sand-300 shadow-xl space-y-4 animate-in fade-in zoom-in-95 duration-150">
          <div className="flex items-center justify-between border-b border-sand-200 pb-4">
            <div>
              <span className="text-xs font-bold text-emerald-700 uppercase">DOCUMENT PREVIEW & VALIDATION</span>
              <h3 className="text-lg font-black text-sand-900 mt-0.5">{uploadResult.filename || 'Uploaded Document'}</h3>
            </div>
            <div className="flex items-center gap-2">
              <span className="px-3 py-1 rounded-full text-xs font-bold bg-sand-100 text-sand-800">
                Detected: {uploadResult.detected_type || 'Unknown'} ({Math.round((uploadResult.confidence_score || 1.0) * 100)}% Confidence)
              </span>
            </div>
          </div>

          {/* Validation Metrics Grid */}
          <div className="grid grid-cols-4 gap-3 text-center text-xs">
            <div className="p-3 rounded-2xl bg-sand-50 border border-sand-200">
              <div className="text-sand-500 font-medium">Total Rows</div>
              <div className="text-lg font-black text-sand-900">{uploadResult.record_count ?? 0}</div>
            </div>
            <div className="p-3 rounded-2xl bg-emerald-50 border border-emerald-200">
              <div className="text-emerald-700 font-medium">Valid Records</div>
              <div className="text-lg font-black text-emerald-900">{uploadResult.valid_count ?? 0}</div>
            </div>
            <div className="p-3 rounded-2xl bg-amber-50 border border-amber-200">
              <div className="text-amber-700 font-medium">Warnings</div>
              <div className="text-lg font-black text-amber-900">{uploadResult.warning_count ?? 0}</div>
            </div>
            <div className="p-3 rounded-2xl bg-rose-50 border border-rose-200">
              <div className="text-rose-700 font-medium">Errors</div>
              <div className="text-lg font-black text-rose-900">{uploadResult.error_count ?? 0}</div>
            </div>
          </div>

          {/* Data Preview Table */}
          {previewRows.length > 0 && (
            <div className="border border-sand-200 rounded-2xl overflow-hidden text-xs">
              <div className="bg-sand-100 px-4 py-2 font-bold text-sand-800 border-b border-sand-200">
                Preview Sample (First {previewRows.length} rows)
              </div>
              <div className="overflow-x-auto max-h-48">
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="bg-sand-50 border-b border-sand-200">
                      {previewCols.map((col, idx) => (
                        <th key={idx} className="p-2.5 font-bold text-sand-700">{String(col)}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {previewRows.map((row: any, idx: number) => (
                      <tr key={idx} className="border-b border-sand-100 hover:bg-sand-50">
                        {previewCols.map((col, cidx) => {
                          const val = row ? row[col] : '';
                          const displayVal = typeof val === 'object' ? JSON.stringify(val) : String(val ?? '');
                          return (
                            <td key={cidx} className="p-2.5 text-sand-800">{displayVal}</td>
                          );
                        })}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Inline Validation Errors List if any */}
          {Array.isArray(uploadResult.errors) && uploadResult.errors.length > 0 && (
            <div className="border border-rose-200 bg-rose-50/50 rounded-2xl p-4 space-y-2 text-xs">
              <div className="font-bold text-rose-900">Validation Errors ({uploadResult.errors.length}):</div>
              <div className="max-h-36 overflow-y-auto space-y-1 font-mono text-[11px]">
                {uploadResult.errors.map((err: any, i: number) => {
                  const rawVal = typeof err.raw_value === 'object' ? JSON.stringify(err.raw_value) : String(err.raw_value ?? '');
                  return (
                    <div key={i} className="text-rose-800 bg-white p-2 rounded border border-rose-200 flex items-center justify-between">
                      <span>Row {err.row_number || (i + 1)} [{String(err.column_name || 'Field')}]: {String(err.error_message || 'Validation error')}</span>
                      {rawVal && <span className="text-rose-500 text-[10px]">Got: '{rawVal}'</span>}
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Actions */}
          <div className="flex items-center justify-end gap-3 pt-2">
            {(uploadResult.error_count ?? 0) > 0 && (
              <button
                onClick={() => handleDownloadErrorReport(uploadResult.document_id, uploadResult.filename || 'report')}
                className="px-4 py-2.5 rounded-xl text-xs font-bold bg-rose-100 text-rose-800 hover:bg-rose-200 transition-colors"
              >
                [ Download Error Report ]
              </button>
            )}
            <button
              onClick={() => handleConfirmImport(uploadResult.document_id)}
              disabled={isImporting}
              className="px-6 py-2.5 rounded-xl text-xs font-bold bg-forest-800 text-white hover:bg-forest-900 transition-colors shadow-md disabled:opacity-50"
            >
              {isImporting ? 'Importing Dataset...' : '[ Confirm & Import Data ]'}
            </button>
          </div>
        </div>
      )}

      {/* Uploaded Documents List */}
      <div className="bg-white rounded-3xl border border-sand-300 shadow-xl overflow-hidden">
        <div className="p-5 bg-sand-100 border-b border-sand-200 flex items-center justify-between">
          <h3 className="text-sm font-black text-sand-900">IMPORTED DATASET REGISTRY</h3>
          <span className="text-xs text-sand-500">{documents.length} Total Registered Datasets</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="bg-sand-50 border-b border-sand-200 text-sand-600 font-bold uppercase tracking-wider">
                <th className="p-3.5">Document Name</th>
                <th className="p-3.5">Category</th>
                <th className="p-3.5">Version</th>
                <th className="p-3.5">Records</th>
                <th className="p-3.5">Status</th>
                <th className="p-3.5">Uploaded By</th>
                <th className="p-3.5">Date & Time</th>
                <th className="p-3.5 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-sand-100">
              {documents.length === 0 ? (
                <tr>
                  <td colSpan={8} className="p-8 text-center text-sand-400">
                    No documents uploaded yet. Click "[ + Upload Document ]" to ingest CSV or Excel files.
                  </td>
                </tr>
              ) : (
                documents.map((doc) => (
                  <tr key={doc.id} className="hover:bg-sand-50/80 transition-colors">
                    <td className="p-3.5 font-bold text-sand-900 flex items-center gap-2">
                      <span className="p-1.5 rounded-lg bg-sand-200 text-[10px] uppercase font-bold text-sand-700">
                        {doc.file_type || 'CSV'}
                      </span>
                      <span>{doc.filename}</span>
                    </td>
                    <td className="p-3.5 font-semibold text-sand-700">{doc.document_type}</td>
                    <td className="p-3.5 font-bold text-forest-800">V{doc.version}</td>
                    <td className="p-3.5 font-bold text-sand-900">{(doc.record_count || 0).toLocaleString()}</td>
                    <td className="p-3.5">
                      <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold ${
                        doc.status === 'IMPORTED' ? 'bg-emerald-100 text-emerald-800' :
                        doc.status === 'VALIDATED' ? 'bg-blue-100 text-blue-800' :
                        'bg-rose-100 text-rose-800'
                      }`}>
                        {doc.status === 'IMPORTED' ? '✓ Imported' : doc.status}
                      </span>
                    </td>
                    <td className="p-3.5 text-sand-600">{doc.uploaded_by}</td>
                    <td className="p-3.5 text-sand-500">
                      {doc.created_at ? new Date(doc.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : ''}
                    </td>
                    <td className="p-3.5 text-right">
                      <button
                        onClick={() => handleViewPreview(doc.id)}
                        className="px-3 py-1 rounded-lg text-[11px] font-bold bg-sand-200 text-sand-800 hover:bg-sand-300 transition-colors"
                      >
                        Preview
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export const DataImportCenter: React.FC = () => (
  <DataImportErrorBoundary>
    <DataImportCenterContent />
  </DataImportErrorBoundary>
);
