import { useParams, useNavigate } from "react-router-dom";
import {
  ArrowLeft,
  Download,
  FileCheck,
  AlertTriangle,
  Shield,
  Clock,
  Hash,
  FileType,
  ShieldCheck,
  Activity,
  Brain,
  Cpu,
  BarChart3,
  Network,
  Settings,
  RefreshCw,
  FolderOpen,
} from "lucide-react";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Navbar } from "@/components/Navbar";
import { Footer } from "@/components/Footer";
import { Progress } from "@/components/ui/progress";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ConfidenceHeatmap, AlgorithmDetectionChart, FunctionPredictionsTable } from "@/components/AnalysisCharts";
import { JsonViewer } from "@/components/JsonViewer";
import { AnalysisSummary, AnalysisStatusIndicator } from "@/components/AnalysisSummary";
import { CFGVisualization } from "@/components/CFGVisualization";
import { FunctionAnalysisDetails } from "@/components/FunctionAnalysisDetails";
import { OpcodeAnalysis } from "@/components/OpcodeAnalysis";
import { FileSystemAnalysis } from "@/components/FileSystemAnalysis";
import { LLMAnalysisCard } from "@/components/LLMAnalysis";
import { HardTargetAnalysis } from "@/components/HardTargetAnalysis";
import { PipelineVisualization } from "@/components/PipelineVisualization";

import { useEffect, useState } from "react";
import { API_CONFIG } from "@/config/api";

interface JobAnalysisData {
  job_id: string;
  job_storage_data: any;
  qiling_output: any[];
  pipeline_output: any[];
  child_jobs: any[];
  related_files: {
    job_storage_files: number;
    qiling_output_files: number;
    pipeline_output_files: number;
    child_job_count: number;
  };
}

const JobAnalysis = () => {
  const { jobId } = useParams();
  const navigate = useNavigate();

  const [analysisData, setAnalysisData] = useState<JobAnalysisData | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  /** Fetch comprehensive analysis data from backend */
  const fetchAnalysisData = async (showRefreshState = false) => {
    try {
      if (showRefreshState) setRefreshing(true);
      else setLoading(true);

      const res = await fetch(`${API_CONFIG.BASE_URL}/job/${jobId}/complete-analysis`);
      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || 'Failed to fetch analysis data');
      }

      setAnalysisData(data);
      setError(null);
    } catch (e) {
      console.error("Error loading analysis data:", e);
      setError(e instanceof Error ? e.message : 'Unknown error occurred');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    if (jobId) {
      fetchAnalysisData();
    }
  }, [jobId]);

  /** Download analysis report */
  const downloadReport = () => {
    const blob = new Blob([JSON.stringify(analysisData, null, 2)], {
      type: "application/json",
    });

    const url = URL.createObjectURL(blob);

    const a = document.createElement("a");
    a.href = url;
    a.download = `vestigo-analysis-${jobId}.json`;
    a.click();

    URL.revokeObjectURL(url);
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-background">
        <Navbar />
        <section className="pt-32 pb-20 px-6">
          <div className="container mx-auto max-w-5xl">
            <div className="flex items-center justify-center min-h-[400px]">
              <div className="text-center">
                <RefreshCw className="w-8 h-8 mx-auto mb-4 animate-spin text-primary" />
                <h2 className="text-2xl font-semibold mb-2">Loading Analysis Data</h2>
                <p className="text-muted-foreground">Please wait while we fetch your analysis results...</p>
              </div>
            </div>
          </div>
        </section>
        <Footer />
      </div>
    );
  }

  if (error || !analysisData) {
    return (
      <div className="min-h-screen bg-background">
        <Navbar />
        <section className="pt-32 pb-20 px-6">
          <div className="container mx-auto max-w-5xl">
            <Button
              variant="ghost"
              onClick={() => navigate("/jobs")}
              className="mb-6 -ml-4"
            >
              <ArrowLeft className="w-4 h-4 mr-2" /> Back to Dashboard
            </Button>
            
            <div className="text-center">
              <AlertTriangle className="w-16 h-16 mx-auto text-red-500 mb-4" />
              <h1 className="text-4xl font-bold mb-4">Analysis Not Found</h1>
              <p className="text-muted-foreground mb-4">
                {error || "Could not load analysis data for this job."}
              </p>
              <div className="space-x-4">
                <Button onClick={() => fetchAnalysisData()} className="bg-primary">
                  <RefreshCw className="w-4 h-4 mr-2" />
                  Retry
                </Button>
                <Button variant="outline" onClick={() => navigate("/jobs")}>
                  Back to Dashboard
                </Button>
              </div>
            </div>
          </div>
        </section>
        <Footer />
      </div>
    );
  }

  const jobData = analysisData.job_storage_data;
  const relatedFiles = analysisData.related_files;

  return (
    <div className="min-h-screen bg-background">
      <Navbar />

      <section className="pt-32 pb-20 px-6">
        <div className="container mx-auto max-w-7xl">
          {/* Back Button & Header */}
          <div className="flex items-center justify-between mb-8">
            <Button
              variant="ghost"
              onClick={() => navigate("/jobs")}
              className="-ml-4"
            >
              <ArrowLeft className="w-4 h-4 mr-2" /> Back to Dashboard
            </Button>

            <div className="flex gap-3">
              <Button 
                variant="outline" 
                onClick={() => fetchAnalysisData(true)}
                disabled={refreshing}
              >
                <RefreshCw className={`w-4 h-4 mr-2 ${refreshing ? 'animate-spin' : ''}`} />
                Refresh
              </Button>
              <Button onClick={downloadReport} className="bg-primary">
                <Download className="w-4 h-4 mr-2" /> Download Report
              </Button>
            </div>
          </div>

          {/* Job Overview */}
          <div className="mb-8">
            <h1 className="text-4xl md:text-5xl font-display font-bold mb-2">
              {jobData?.filename || 'Binary Analysis'}
            </h1>
            <p className="text-muted-foreground text-lg">Job ID: {jobId}</p>
          </div>

          {/* Analysis Summary */}
          <AnalysisSummary jobData={jobData} />

          {/* Analysis Status */}
          <AnalysisStatusIndicator 
            status={jobData?.status as string || 'processing'}
            hasFeatureExtraction={!!(jobData as Record<string, unknown>)?.feature_extraction_results}
            hasMLClassification={!!((jobData as Record<string, unknown>)?.feature_extraction_results as Record<string, unknown>)?.ml_classification}
            hasQilingAnalysis={!!(jobData as Record<string, unknown>)?.qiling_dynamic_results}
            hasLLMAnalysis={!!(jobData as Record<string, unknown>)?.llm_analysis_results}
          />

          {/* Analysis Tabs */}
          <Tabs defaultValue="overview" className="w-full">
            <TabsList className="grid w-full grid-cols-9">
              <TabsTrigger value="overview">Overview</TabsTrigger>
              <TabsTrigger value="pipeline">Pipeline</TabsTrigger>
              <TabsTrigger value="ml-classification">ML Analysis</TabsTrigger>
              <TabsTrigger value="filesystem">Filesystem</TabsTrigger>
              <TabsTrigger value="features">Features</TabsTrigger>
              <TabsTrigger value="qiling">Dynamic</TabsTrigger>
              <TabsTrigger value="llm">Agent</TabsTrigger>
              <TabsTrigger value="hard-target">Hard Target</TabsTrigger>
              <TabsTrigger value="file-info">File Info</TabsTrigger>
            </TabsList>

            <TabsContent value="overview" className="space-y-6">
              <FileMetadataCard jobData={jobData} />
              <AnalysisOverviewCard jobData={jobData} />
            </TabsContent>

            <TabsContent value="pipeline" className="space-y-6">
              <PipelineVisualization
                jobId={jobId || ''}
                routingDecision={jobData?.routing_decision || 'unknown'}
                routingReason={jobData?.routing_reason || 'No reason provided'}
                bootloaders={jobData?.bootloaders || []}
                binaries={(jobData as Record<string, unknown>)?.feature_extraction_results 
                  ? ((jobData as Record<string, unknown>).feature_extraction_results as Record<string, unknown>).binaries as any[]
                  : []}
                status={jobData?.status || 'processing'}
                autoRefresh={jobData?.status !== 'complete' && jobData?.status !== 'failed'}
              />
            </TabsContent>

            <TabsContent value="file-info" className="space-y-6">
              <DetailedFileInfoCard jobData={jobData} />
            </TabsContent>

            <TabsContent value="ml-classification" className="space-y-6">
              <MLClassificationCard jobData={jobData} />
              <GNNClassificationCard jobData={jobData} />
            </TabsContent>

            <TabsContent value="filesystem" className="space-y-6">
              <FileSystemAnalysis 
                featureResults={(jobData as Record<string, unknown>)?.feature_extraction_results as Record<string, unknown> | null} 
              />
            </TabsContent>

            <TabsContent value="features" className="space-y-6">
              <FeatureExtractionCard jobData={jobData} />
            </TabsContent>

            <TabsContent value="qiling" className="space-y-6">
              <QilingAnalysisCard qilingData={jobData} />
            </TabsContent>

            <TabsContent value="llm" className="space-y-6">
              <LLMAnalysisCard 
                llmData={(jobData as Record<string, unknown>)?.llm_analysis_results as Record<string, unknown> | null}
                qilingData={jobData as Record<string, unknown> | null}
                jobId={jobId}
              />
            </TabsContent>

            <TabsContent value="hard-target" className="space-y-6">
              <HardTargetAnalysis 
                hardTargetInfo={((jobData as Record<string, unknown>)?.analysis_results as Record<string, unknown>)?.hard_target_info as Record<string, unknown>}
                jobData={jobData as Record<string, unknown>}
              />
            </TabsContent>

            <TabsContent value="raw-data" className="space-y-6">
              <RawDataCard analysisData={analysisData} />
            </TabsContent>
          </Tabs>
        </div>
      </section>

      <Footer />
    </div>
  );
};

// Component for File Metadata Display
const FileMetadataCard = ({ jobData }: { jobData: unknown }) => {
  // Safely extract file information from the job data
  const getFileInfo = () => {
    if (!jobData || typeof jobData !== 'object') return {};
    
    const data = jobData as Record<string, unknown>;
    
    // Extract architecture from feature_extraction_results
    let arch = 'Unknown';
    const featureResults = data.feature_extraction_results as Record<string, unknown>;
    if (featureResults && featureResults.functions && Array.isArray(featureResults.functions) && featureResults.functions.length > 0) {
      const firstFunc = featureResults.functions[0] as Record<string, unknown>;
      arch = (firstFunc.arch as string) || 'Unknown';
    }
    
    return {
      filename: data.filename as string,
      file_type: data.file_type as string,
      file_size: data.file_size as number,
      hash: data.hash as string,
      arch: arch,
      upload_time: data.upload_time as string,
      status: data.status as string,
    };
  };

  const fileInfo = getFileInfo();

  const formatFileSize = (bytes: number | undefined): string => {
    if (!bytes || typeof bytes !== 'number') return 'Unknown';
    
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(2)} KB`;
    if (bytes < 1024 * 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(2)} MB`;
    return `${(bytes / 1024 / 1024 / 1024).toFixed(2)} GB`;
  };

  const getFileTypeIcon = (fileType: string | undefined) => {
    if (!fileType) return <FileType className="w-4 h-4 text-gray-500" />;
    
    const type = fileType.toLowerCase();
    if (type.includes('elf')) return <Shield className="w-4 h-4 text-blue-500" />;
    if (type.includes('pe')) return <Shield className="w-4 h-4 text-green-500" />;
    if (type.includes('mach-o')) return <Shield className="w-4 h-4 text-purple-500" />;
    if (type.includes('firmware')) return <Cpu className="w-4 h-4 text-orange-500" />;
    return <FileType className="w-4 h-4 text-gray-500" />;
  };

  const getStatusBadge = (status: string | undefined) => {
    if (!status) return null;
    
    const statusLower = status.toLowerCase();
    let variant: "default" | "secondary" | "destructive" | "outline" = "outline";
    let className = "";
    
    if (statusLower.includes('complete') || statusLower.includes('success')) {
      variant = "default";
      className = "bg-green-100 text-green-800 border-green-200";
    } else if (statusLower.includes('processing') || statusLower.includes('running')) {
      variant = "outline";
      className = "bg-blue-100 text-blue-800 border-blue-200";
    } else if (statusLower.includes('failed') || statusLower.includes('error')) {
      variant = "destructive";
    }
    
    return (
      <Badge variant={variant} className={className}>
        {status}
      </Badge>
    );
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          {getFileTypeIcon(fileInfo.file_type)}
          File Information
        </CardTitle>
        <CardDescription>
          Basic file metadata and properties
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          <div>
            <p className="text-sm font-medium text-muted-foreground mb-1">Filename</p>
            <p className="font-medium break-all">{fileInfo.filename || 'Unknown'}</p>
          </div>
          
          <div>
            <p className="text-sm font-medium text-muted-foreground mb-1">File Type</p>
            <div className="flex items-center gap-2">
              {getFileTypeIcon(fileInfo.file_type)}
              <span className="font-mono text-sm">{fileInfo.file_type || 'Unknown'}</span>
            </div>
          </div>
          
          <div>
            <p className="text-sm font-medium text-muted-foreground mb-1">Architecture</p>
            <p className="font-mono">{fileInfo.arch || 'Unknown'}</p>
          </div>
          
          <div>
            <p className="text-sm font-medium text-muted-foreground mb-1">File Size</p>
            <p className="font-medium">{formatFileSize(fileInfo.file_size)}</p>
          </div>
          
          <div>
            <p className="text-sm font-medium text-muted-foreground mb-1">Status</p>
            {getStatusBadge(fileInfo.status)}
          </div>
          
          {fileInfo.upload_time && (
            <div>
              <p className="text-sm font-medium text-muted-foreground mb-1">Upload Time</p>
              <p className="text-sm">{new Date(fileInfo.upload_time).toLocaleString()}</p>
            </div>
          )}
          
          {fileInfo.hash && (
            <div className="md:col-span-2 lg:col-span-3">
              <p className="text-sm font-medium text-muted-foreground mb-1">File Hash</p>
              <div className="flex items-center gap-2 p-2 bg-muted rounded-md">
                <Hash className="w-4 h-4 text-muted-foreground flex-shrink-0" />
                <p className="font-mono text-sm break-all">{fileInfo.hash}</p>
              </div>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
};

// Component for Analysis Overview
const AnalysisOverviewCard = ({ jobData }: { jobData: unknown }) => {
  const getAnalysisInfo = () => {
    if (!jobData || typeof jobData !== 'object') return {};
    
    const data = jobData as Record<string, unknown>;
    const analysisResults = data.analysis_results as Record<string, unknown>;
    
    return {
      routing: analysisResults?.routing as { decision?: string; reason?: string },
      extraction: analysisResults?.extraction as { was_extracted?: boolean },
      file_info: analysisResults?.file_info as { detected_type?: string },
      workspace_path: analysisResults?.analysis_workspace as string,
      bootloaders: analysisResults?.bootloaders as unknown[],
    };
  };

  const analysisInfo = getAnalysisInfo();

  const getAnalysisPathBadge = (decision: string | undefined) => {
    if (!decision) return null;
    
    let className = "text-gray-800 bg-gray-100 border-gray-200";
    
    if (decision.includes('PATH_A_BARE_METAL')) {
      className = "text-blue-800 bg-blue-100 border-blue-200";
    } else if (decision.includes('PATH_B_LINUX_FS')) {
      className = "text-green-800 bg-green-100 border-green-200";
    } else if (decision.includes('BOOTLOADER')) {
      className = "text-purple-800 bg-purple-100 border-purple-200";
    } else if (decision.includes('CRYPTO')) {
      className = "text-orange-800 bg-orange-100 border-orange-200";
    }
    
    return (
      <Badge variant="outline" className={className}>
        {decision}
      </Badge>
    );
  };

  const getExtractionIcon = (extracted: boolean | undefined) => {
    if (extracted === true) {
      return <ShieldCheck className="w-4 h-4 text-green-500" />;
    } else if (extracted === false) {
      return <AlertTriangle className="w-4 h-4 text-orange-500" />;
    }
    return <Shield className="w-4 h-4 text-gray-500" />;
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Settings className="w-5 h-5" />
          Analysis Overview
        </CardTitle>
        <CardDescription>
          Analysis routing, extraction, and processing details
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-6">
          {/* Analysis Path */}
          {analysisInfo.routing?.decision && (
            <div>
              <p className="text-sm font-medium text-muted-foreground mb-2">Analysis Path</p>
              {getAnalysisPathBadge(analysisInfo.routing.decision)}
              {analysisInfo.routing.reason && (
                <p className="text-sm mt-2 p-3 bg-muted rounded-lg">
                  {analysisInfo.routing.reason}
                </p>
              )}
            </div>
          )}

          {/* Extraction Status */}
          {analysisInfo.extraction && (
            <div>
              <p className="text-sm font-medium text-muted-foreground mb-2">Extraction Status</p>
              <div className="flex items-center gap-2">
                {getExtractionIcon(analysisInfo.extraction.was_extracted)}
                <Badge 
                  variant={analysisInfo.extraction.was_extracted ? "default" : "secondary"}
                  className={analysisInfo.extraction.was_extracted ? 
                    "bg-green-100 text-green-800 border-green-200" : 
                    "bg-gray-100 text-gray-800 border-gray-200"
                  }
                >
                  {analysisInfo.extraction.was_extracted ? "Successfully Extracted" : "No Extraction Needed"}
                </Badge>
              </div>
            </div>
          )}

          {/* Detected File Type */}
          {analysisInfo.file_info?.detected_type && (
            <div>
              <p className="text-sm font-medium text-muted-foreground mb-2">Detected Type</p>
              <Badge variant="outline">
                {analysisInfo.file_info.detected_type}
              </Badge>
            </div>
          )}

          {/* Bootloaders Found */}
          {analysisInfo.bootloaders && Array.isArray(analysisInfo.bootloaders) && analysisInfo.bootloaders.length > 0 && (
            <div>
              <p className="text-sm font-medium text-muted-foreground mb-2">Bootloaders Detected</p>
              <Badge variant="outline" className="text-purple-800 bg-purple-100 border-purple-200">
                {analysisInfo.bootloaders.length} bootloader(s) found
              </Badge>
              <p className="text-sm text-muted-foreground mt-1">
                Separate analysis jobs created for secure boot analysis
              </p>
            </div>
          )}

          {/* Workspace Path */}
          {analysisInfo.workspace_path && (
            <div>
              <p className="text-sm font-medium text-muted-foreground mb-2">Analysis Workspace</p>
              <div className="flex items-center gap-2 p-2 bg-muted rounded-md">
                <FolderOpen className="w-4 h-4 text-muted-foreground flex-shrink-0" />
                <p className="font-mono text-sm break-all">{analysisInfo.workspace_path}</p>
              </div>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
};

// Component for Detailed File Info
const DetailedFileInfoCard = ({ jobData }: { jobData: any }) => (
  <Card>
    <CardHeader>
      <CardTitle>Detailed File Analysis</CardTitle>
      <CardDescription>
        Complete file metadata and analysis information
      </CardDescription>
    </CardHeader>
    <CardContent>
      <pre className="bg-muted p-4 rounded-lg overflow-auto text-sm">
        {JSON.stringify(jobData || {}, null, 2)}
      </pre>
    </CardContent>
  </Card>
);

// Component for ML Classification Results
const MLClassificationCard = ({ jobData }: { jobData: unknown }) => {
  const getMLData = () => {
    if (!jobData || typeof jobData !== 'object') return null;
    
    const data = jobData as Record<string, unknown>;
    const featureResults = data.feature_extraction_results as Record<string, unknown>;
    const mlClassification = featureResults?.ml_classification as Record<string, unknown>;
    
    return mlClassification || null;
  };

  const mlData = getMLData();

  if (!mlData) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Brain className="w-5 h-5" />
            Machine Learning Classification
          </CardTitle>
          <CardDescription>
            AI-powered cryptographic algorithm detection results
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="text-center py-8">
            <Brain className="w-12 h-12 mx-auto mb-4 text-muted-foreground" />
            <p className="text-muted-foreground">
              ML classification data not available yet. Analysis may still be in progress.
            </p>
          </div>
        </CardContent>
      </Card>
    );
  }

  const fileSummary = mlData.file_summary as Record<string, unknown>;
  const functionPredictions = mlData.function_predictions as Array<{
    function_name: string;
    function_address: string;
    predicted_algorithm: string;
    confidence: number;
    is_crypto: boolean;
    top_3_predictions: Array<{
      rank: number;
      algorithm: string;
      probability: number;
      confidence_percent: number;
      algorithm_type: string;
    }>;
  }>;

  const confidenceScores = fileSummary?.confidence_scores as Record<string, {
    avg_probability: number;
    max_probability: number;
    functions_with_significant_probability: number;
  }>;

  const detectedAlgorithms = fileSummary?.detected_algorithms as string[];
  const algorithmCounts = fileSummary?.algorithm_counts as Record<string, number>;

  return (
    <div className="space-y-6">
      {/* File Status Overview */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Brain className="w-5 h-5" />
            ML Classification Overview
          </CardTitle>
          <CardDescription>
            AI-powered cryptographic algorithm detection results
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="text-center p-4 bg-muted rounded-lg">
              <p className="text-sm text-muted-foreground mb-1">File Status</p>
              <Badge className={
                (fileSummary?.file_status as string)?.toLowerCase().includes('crypto') 
                  ? 'bg-red-100 text-red-800 border-red-200'
                  : 'bg-green-100 text-green-800 border-green-200'
              }>
                {(fileSummary?.file_status as string)?.replace('_', ' ').toUpperCase() || 'UNKNOWN'}
              </Badge>
            </div>
            
            <div className="text-center p-4 bg-muted rounded-lg">
              <p className="text-sm text-muted-foreground mb-1">Crypto Percentage</p>
              <div className="text-2xl font-bold">
                {typeof fileSummary?.crypto_percentage === 'number' 
                  ? `${fileSummary.crypto_percentage}%` 
                  : 'N/A'}
              </div>
            </div>
            
            <div className="text-center p-4 bg-muted rounded-lg">
              <p className="text-sm text-muted-foreground mb-1">Average Confidence</p>
              <div className="text-2xl font-bold">
                {typeof fileSummary?.average_confidence === 'number' 
                  ? `${(fileSummary.average_confidence * 100).toFixed(1)}%` 
                  : 'N/A'}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Confidence Heatmap */}
      {confidenceScores && <ConfidenceHeatmap confidenceScores={confidenceScores} />}

      {/* Algorithm Detection Chart */}
      {algorithmCounts && detectedAlgorithms && (
        <AlgorithmDetectionChart 
          algorithmCounts={algorithmCounts} 
          detectedAlgorithms={detectedAlgorithms} 
        />
      )}

      {/* Function Predictions Table */}
      {functionPredictions && functionPredictions.length > 0 && (
        <FunctionPredictionsTable functionPredictions={functionPredictions} />
      )}
    </div>
  );
};

// Component for Feature Extraction Results
const FeatureExtractionCard = ({ jobData }: { jobData: unknown }) => {
  const getFeatureData = () => {
    if (!jobData || typeof jobData !== 'object') return null;
    
    const data = jobData as Record<string, unknown>;
    return data.feature_extraction_results as Record<string, unknown> || null;
  };

  const featureData = getFeatureData();

  const renderBinarySections = (summary: Record<string, unknown>) => {
    const binarySections = summary.binary_sections as Record<string, unknown>;
    if (!binarySections) return null;

    const sections = [
      { name: 'Text Section', key: 'text_size', color: 'bg-blue-500' },
      { name: 'RO Data', key: 'rodata_size', color: 'bg-green-500' },
      { name: 'Data Section', key: 'data_size', color: 'bg-yellow-500' },
      { name: 'BSS Section', key: 'bss_size', color: 'bg-purple-500' },
    ];

    const totalSize = sections.reduce((sum, section) => {
      const size = binarySections[section.key] as number || 0;
      return sum + size;
    }, 0);

    return (
      <div className="space-y-4">
        <h4 className="text-lg font-semibold">Binary Sections</h4>
        <div className="space-y-3">
          {sections.map((section) => {
            const size = binarySections[section.key] as number || 0;
            const percentage = totalSize > 0 ? (size / totalSize) * 100 : 0;
            
            return (
              <div key={section.key} className="flex items-center gap-3">
                <div className={`w-4 h-4 rounded ${section.color}`} />
                <div className="flex-1 min-w-0">
                  <div className="flex justify-between items-center mb-1">
                    <span className="font-medium">{section.name}</span>
                    <span className="text-sm text-muted-foreground">
                      {(size / 1024).toFixed(1)} KB ({percentage.toFixed(1)}%)
                    </span>
                  </div>
                  <Progress value={percentage} className="h-2" />
                </div>
              </div>
            );
          })}
        </div>
      </div>
    );
  };

  const renderFunctionSummary = (summary: Record<string, unknown>) => {
    const totalFunctions = summary.total_functions as number;
    const metadata = summary.metadata as Record<string, unknown> | undefined;
    const totalTables = metadata?.total_tables_detected as number;
    const avgComplexity = summary.average_cyclomatic_complexity as number;
    const avgEntropy = summary.average_entropy as number;

    return (
      <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
        <div className="text-center p-3 bg-muted rounded-lg">
          <div className="text-2xl font-bold">{totalFunctions || 0}</div>
          <div className="text-sm text-muted-foreground">Functions</div>
        </div>
        <div className="text-center p-3 bg-muted rounded-lg">
          <div className="text-2xl font-bold">{totalTables || 0}</div>
          <div className="text-sm text-muted-foreground">Tables</div>
        </div>
        {/* <div className="text-center p-3 bg-muted rounded-lg">
          <div className="text-2xl font-bold">
            {typeof avgComplexity === 'number' ? avgComplexity.toFixed(1) : 'N/A'}
          </div>
          <div className="text-sm text-muted-foreground">Avg Complexity</div>
        </div> */}
        <div className="text-center p-3 bg-muted rounded-lg">
          <div className="text-2xl font-bold">
            {typeof avgEntropy === 'number' ? avgEntropy.toFixed(2) : 'N/A'}
          </div>
          <div className="text-sm text-muted-foreground">Avg Entropy</div>
        </div>
      </div>
    );
  };

  if (!featureData) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Activity className="w-5 h-5" />
            Feature Extraction
          </CardTitle>
          <CardDescription>
            Binary analysis features and characteristics
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="text-center py-8">
            <Activity className="w-12 h-12 mx-auto mb-4 text-muted-foreground" />
            <p className="text-muted-foreground">
              Feature extraction data not available yet. Analysis may still be in progress.
            </p>
          </div>
        </CardContent>
      </Card>
    );
  }

  const summary = featureData.summary as Record<string, unknown>;
  const functions = featureData.functions as Array<Record<string, unknown>>;

  return (
    <div className="space-y-6">
      {/* Summary Overview */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Activity className="w-5 h-5" />
            Feature Extraction Overview
          </CardTitle>
          <CardDescription>
            Binary analysis summary and metadata
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Tabs defaultValue="overview" className="w-full">
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="overview">Overview</TabsTrigger>
              <TabsTrigger value="sections">Binary Sections</TabsTrigger>
            </TabsList>

            <TabsContent value="overview" className="space-y-6 mt-6">
              {summary && renderFunctionSummary(summary)}
            </TabsContent>

            <TabsContent value="sections" className="space-y-6 mt-6">
              {summary && renderBinarySections(summary)}
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>

      {/* Detailed Function Analysis */}
      {functions && functions.length > 0 && (
        <>
          {functions.map((func, idx) => {
            // Only show if we have the necessary data structure
            if (!func.graph_level || !func.edge_level || !func.node_level) {
              return null;
            }

            return (
              <div key={idx}>
                {/* Function Details */}
                <FunctionAnalysisDetails functionData={func as never} />

                {/* CFG Visualization */}
                <CFGVisualization
                  edges={func.edge_level as never[]}
                  nodes={func.node_level as never[]}
                  graphMetrics={func.graph_level as never}
                />

                {/* Opcode Analysis */}
                {func.node_level && Array.isArray(func.node_level) && func.node_level.length > 0 && (
                  <OpcodeAnalysis
                    opcodeHistogram={(func.node_level as Array<Record<string, unknown>>)[0]?.opcode_histogram as Record<string, number> || {}}
                    opcodeRatios={(func.node_level as Array<Record<string, unknown>>)[0]?.opcode_ratios as never || {}}
                    instructionSequence={func.instruction_sequence as never || { unique_ngram_count: 0, top_5_bigrams: [] }}
                  />
                )}
              </div>
            );
          })}
        </>
      )}
    </div>
  );
};  

// Component for GNN Classification Results
const GNNClassificationCard = ({ jobData }: { jobData: unknown }) => {
  const getGNNData = () => {
    if (!jobData || typeof jobData !== 'object') return null;
    
    const data = jobData as Record<string, unknown>;
    const featureExtraction = data.feature_extraction_results as Record<string, unknown>;
    if (!featureExtraction) return null;
    
    return featureExtraction.gnn_classification as Record<string, unknown> || null;
  };

  const gnnData = getGNNData();

  if (!gnnData || gnnData.status !== 'completed') {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Network className="w-5 h-5" />
            GNN Classification (Graph Neural Network)
          </CardTitle>
          <CardDescription>
            Advanced graph-based cryptographic pattern recognition
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="text-center py-8">
            <Network className="w-12 h-12 mx-auto mb-4 text-muted-foreground" />
            <p className="text-muted-foreground">
              {gnnData?.status === 'failed' 
                ? 'GNN classification failed or unavailable.'
                : 'GNN classification data not available yet.'}
            </p>
          </div>
        </CardContent>
      </Card>
    );
  }

  const summary = gnnData.summary as Record<string, unknown>;
  const functionPredictions = gnnData.function_predictions as Array<{
    function_name: string;
    function_address: string;
    predicted_class: string;
    confidence: number;
    is_crypto: boolean;
    probabilities: Record<string, number>;
    graph_features?: {
      num_nodes: number;
      num_edges: number;
    };
  }>;
  const algorithmDistribution = gnnData.algorithm_distribution as Record<string, number>;

  // Get top algorithm predictions from probabilities
  const getTopPredictions = (probabilities: Record<string, number>, topN = 5) => {
    return Object.entries(probabilities)
      .sort(([, a], [, b]) => b - a)
      .slice(0, topN)
      .map(([algorithm, probability]) => ({ algorithm, probability }));
  };

  return (
    <div className="space-y-6">
      {/* GNN Overview */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Network className="w-5 h-5" />
            GNN Classification Overview
          </CardTitle>
          <CardDescription>
            Graph Neural Network analysis using control flow and data flow patterns
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="text-center p-4 bg-muted rounded-lg">
              <p className="text-sm text-muted-foreground mb-1">Total Functions</p>
              <div className="text-2xl font-bold">
                {Number(summary?.total_functions) || 0}
              </div>
            </div>
            
            <div className="text-center p-4 bg-muted rounded-lg">
              <p className="text-sm text-muted-foreground mb-1">Crypto Functions</p>
              <div className="text-2xl font-bold text-red-600">
                {Number(summary?.crypto_functions) || 0}
              </div>
            </div>
            
            <div className="text-center p-4 bg-muted rounded-lg">
              <p className="text-sm text-muted-foreground mb-1">Crypto Percentage</p>
              <div className="text-2xl font-bold">
                {typeof summary?.crypto_percentage === 'number' 
                  ? `${summary.crypto_percentage.toFixed(1)}%` 
                  : 'N/A'}
              </div>
            </div>
          </div>

          {/* Algorithm Distribution */}
          {algorithmDistribution && Object.keys(algorithmDistribution).length > 0 && (
            <div className="mt-6">
              <h4 className="font-semibold mb-3">Algorithm Distribution</h4>
              <div className="flex flex-wrap gap-2">
                {Object.entries(algorithmDistribution).map(([algo, count]) => (
                  <Badge 
                    key={algo} 
                    className="bg-purple-100 text-purple-800 border-purple-200"
                  >
                    {algo}: {count}
                  </Badge>
                ))}
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Function Predictions */}
      {functionPredictions && functionPredictions.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>GNN Function Analysis</CardTitle>
            <CardDescription>
              Detailed predictions for each analyzed function
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {functionPredictions.map((func, idx) => {
                const topPredictions = getTopPredictions(func.probabilities, 5);
                
                return (
                  <div key={idx} className="border rounded-lg p-4 bg-muted/30">
                    <div className="flex items-start justify-between mb-3">
                      <div>
                        <h4 className="font-semibold text-lg">
                          {func.function_name}
                        </h4>
                        <p className="text-sm text-muted-foreground">
                          Address: {func.function_address}
                        </p>
                      </div>
                      <Badge className={
                        func.is_crypto 
                          ? 'bg-red-100 text-red-800 border-red-200'
                          : 'bg-green-100 text-green-800 border-green-200'
                      }>
                        {func.is_crypto ? 'Crypto' : 'Non-Crypto'}
                      </Badge>
                    </div>

                    <div className="mb-3">
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-sm font-medium">
                          Predicted: {func.predicted_class}
                        </span>
                        <span className="text-sm text-muted-foreground">
                          Confidence: {(func.confidence * 100).toFixed(2)}%
                        </span>
                      </div>
                      <Progress value={func.confidence * 100} className="h-2" />
                    </div>

                    {/* Graph Features */}
                    {func.graph_features && (
                      <div className="grid grid-cols-2 gap-2 mb-3 text-sm">
                        <div className="flex items-center gap-2">
                          <Network className="w-4 h-4 text-muted-foreground" />
                          <span>Nodes: {func.graph_features.num_nodes}</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <Activity className="w-4 h-4 text-muted-foreground" />
                          <span>Edges: {func.graph_features.num_edges}</span>
                        </div>
                      </div>
                    )}

                    {/* Top Predictions */}
                    <div>
                      <h5 className="text-sm font-semibold mb-2">Top Algorithm Probabilities:</h5>
                      <div className="space-y-2">
                        {topPredictions.map(({ algorithm, probability }, index) => (
                          <div key={algorithm} className="flex items-center gap-2">
                            <Badge variant="outline" className="min-w-[30px] justify-center">
                              {index + 1}
                            </Badge>
                            <div className="flex-1">
                              <div className="flex items-center justify-between mb-1">
                                <span className="text-sm font-medium">{algorithm}</span>
                                <span className="text-xs text-muted-foreground">
                                  {(probability * 100).toFixed(4)}%
                                </span>
                              </div>
                              <Progress 
                                value={probability * 100} 
                                className="h-1.5"
                              />
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Binary Info */}
      {gnnData.binary_info && gnnData.binary_info !== 'unknown' && (
        <Card>
          <CardHeader>
            <CardTitle>Binary Information</CardTitle>
          </CardHeader>
          <CardContent>
            <pre className="bg-muted p-4 rounded-lg text-sm overflow-auto">
              {JSON.stringify(gnnData.binary_info, null, 2)}
            </pre>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

// Component for Qiling Dynamic Analysis
const QilingAnalysisCard = ({ qilingData }: { qilingData: unknown }) => {
  // Extract qiling results from job data
  const getQilingResults = () => {
    if (!qilingData || typeof qilingData !== 'object') return null;
    
    const data = qilingData as Record<string, unknown>;
    return data.qiling_dynamic_results as Record<string, unknown> || null;
  };

  const qilingResults = getQilingResults();

  if (!qilingResults) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Cpu className="w-5 h-5" />
            Dynamic Analysis (Qiling)
          </CardTitle>
          <CardDescription>
            Runtime behavior and dynamic crypto detection
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="text-center py-8">
            <Cpu className="w-12 h-12 mx-auto mb-4 text-muted-foreground" />
            <p className="text-muted-foreground">
              No dynamic analysis data available.
            </p>
          </div>
        </CardContent>
      </Card>
    );
  }

  const status = qilingResults.status as string;
  const executionTime = qilingResults.execution_time as number;
  const phases = qilingResults.phases as Record<string, unknown>;
  const verdict = qilingResults.verdict as Record<string, unknown>;
  const analysisTimestamp = qilingResults.analysis_timestamp as number;
  const binaryPath = qilingResults.binary_path as string;
  const binaryName = qilingResults.binary_name as string;
  const analysisTool = qilingResults.analysis_tool as string;
  const classificationResults = qilingResults.classification_results;
  const createdAt = qilingResults.created_at as number;
  const updatedAt = qilingResults.updated_at as number;
  const errorMessage = qilingResults.error_message as string;

  const formatTimestamp = (timestamp: number | undefined): string => {
    if (!timestamp || typeof timestamp !== 'number') return 'N/A';
    return new Date(timestamp * 1000).toLocaleString();
  };

  const getStatusBadge = (status: string) => {
    switch (status?.toLowerCase()) {
      case 'completed':
      case 'success':
        return <Badge className="bg-green-100 text-green-800 border-green-200">Success</Badge>;
      case 'failed':
        return <Badge className="bg-red-100 text-red-800 border-red-200">Failed</Badge>;
      case 'timeout':
        return <Badge className="bg-yellow-100 text-yellow-800 border-yellow-200">Timeout</Badge>;
      default:
        return <Badge variant="outline">{status}</Badge>;
    }
  };

  return (
    <div className="space-y-6">
      {/* Binary Information */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileCheck className="w-5 h-5" />
            Binary Information
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <div className="flex flex-col">
                <span className="text-sm text-muted-foreground">Binary Name</span>
                <span className="font-mono text-sm break-all">{binaryName || 'N/A'}</span>
              </div>
              <div className="flex flex-col">
                <span className="text-sm text-muted-foreground">Binary Path</span>
                <span className="font-mono text-xs break-all">{binaryPath || 'N/A'}</span>
              </div>
            </div>
            <div className="space-y-2">
              <div className="flex flex-col">
                <span className="text-sm text-muted-foreground">Analysis Tool</span>
                <Badge variant="outline" className="w-fit">{analysisTool || 'qiling'}</Badge>
              </div>
              <div className="flex flex-col">
                <span className="text-sm text-muted-foreground">Analysis Timestamp</span>
                <span className="text-sm">{formatTimestamp(analysisTimestamp)}</span>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Execution Summary */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Cpu className="w-5 h-5" />
            Dynamic Analysis Summary
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="text-center p-4 bg-muted rounded-lg">
              <p className="text-sm text-muted-foreground mb-1">Status</p>
              {getStatusBadge(status)}
            </div>
            
            <div className="text-center p-4 bg-muted rounded-lg">
              <p className="text-sm text-muted-foreground mb-1">Execution Time</p>
              <div className="text-xl font-bold">
                {typeof executionTime === 'number' ? `${executionTime.toFixed(2)}s` : 'N/A'}
              </div>
            </div>
            
            <div className="text-center p-4 bg-muted rounded-lg">
              <p className="text-sm text-muted-foreground mb-1">Crypto Detection</p>
              <Badge className={
                verdict?.crypto_detected 
                  ? 'bg-red-100 text-red-800 border-red-200'
                  : 'bg-green-100 text-green-800 border-green-200'
              }>
                {verdict?.crypto_detected ? 'Detected' : 'Not Detected'}
              </Badge>
            </div>

            <div className="text-center p-4 bg-muted rounded-lg">
              <p className="text-sm text-muted-foreground mb-1">Confidence</p>
              <div className="space-y-1">
                <Badge className={
                  verdict?.confidence === 'HIGH' ? 'bg-red-100 text-red-800 border-red-200' :
                  verdict?.confidence === 'MEDIUM' ? 'bg-yellow-100 text-yellow-800 border-yellow-200' :
                  'bg-green-100 text-green-800 border-green-200'
                }>
                  {verdict?.confidence as string || 'UNKNOWN'}
                </Badge>
                {typeof verdict?.confidence_score === 'number' && (
                  <div className="text-sm font-semibold">
                    {verdict.confidence_score}%
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Timestamps */}
          <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-3 p-4 bg-muted/50 rounded-lg">
            <div className="flex items-center gap-2">
              <Clock className="w-4 h-4 text-muted-foreground" />
              <div>
                <span className="text-sm text-muted-foreground">Created:</span>
                <span className="ml-2 text-sm font-medium">{formatTimestamp(createdAt)}</span>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Clock className="w-4 h-4 text-muted-foreground" />
              <div>
                <span className="text-sm text-muted-foreground">Updated:</span>
                <span className="ml-2 text-sm font-medium">{formatTimestamp(updatedAt)}</span>
              </div>
            </div>
          </div>

          {/* Verdict Reasons */}
          {verdict?.reasons && Array.isArray(verdict.reasons) && (verdict.reasons as string[]).length > 0 && (
            <div className="mt-4 p-4 text-black bg-blue-50 border border-blue-200 rounded-lg">
              <h4 className="font-semibold mb-2 flex items-center gap-2">
                <ShieldCheck className="w-4 h-4" />
                Detection Reasons:
              </h4>
              <ul className="list-disc list-inside space-y-1 text-sm">
                {(verdict.reasons as string[]).map((reason, idx) => (
                  <li key={idx}>{reason}</li>
                ))}
              </ul>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Analysis Phases */}
      {phases && (
        <Card>
          <CardHeader>
            <CardTitle>Analysis Phases</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {/* Packer Detection */}
              {phases.packer_detection && (
                <div className="p-4 bg-muted/50 rounded-lg">
                  <h4 className="font-semibold mb-2">Packer Detection</h4>
                  <div className="flex items-center gap-2">
                    <span className="text-sm text-muted-foreground">Binary Packed:</span>
                    <Badge variant={
                      (phases.packer_detection as Record<string, unknown>)?.packed 
                        ? "destructive" 
                        : "default"
                    }>
                      {(phases.packer_detection as Record<string, unknown>)?.packed ? 'Yes - Packed Binary' : 'No - Unpacked'}
                    </Badge>
                  </div>
                </div>
              )}

              {/* YARA Analysis */}
              {phases.yara_analysis && (
                <div className="p-4 bg-muted/50 rounded-lg">
                  <h4 className="font-semibold mb-2">YARA Pattern Analysis</h4>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    <div>
                      <span className="text-sm text-muted-foreground">Patterns Detected:</span>
                      <div className="flex flex-wrap gap-1 mt-1">
                        {Array.isArray((phases.yara_analysis as Record<string, unknown>)?.detected) 
                          ? ((phases.yara_analysis as Record<string, unknown>).detected as string[]).map(pattern => (
                              <Badge key={pattern} variant="outline" className="text-xs">
                                {pattern}
                              </Badge>
                            ))
                          : <span className="text-sm text-muted-foreground">None</span>
                        }
                      </div>
                    </div>
                    <div>
                      <span className="text-sm text-muted-foreground">Total Matches:</span>
                      <span className="ml-2 font-medium">
                        {String((phases.yara_analysis as Record<string, unknown>)?.total_matches || 0)}
                      </span>
                    </div>
                  </div>
                </div>
              )}

              {/* Constant Detection */}
              {phases.constant_detection && (
                <div className="p-4 bg-muted/50 rounded-lg">
                  <h4 className="font-semibold mb-2 flex items-center justify-between">
                    <span>Crypto Constants Detection</span>
                    {typeof (phases.constant_detection as Record<string, unknown>)?.count === 'number' && (
                      <Badge variant="outline">
                        {Number((phases.constant_detection as Record<string, unknown>).count)} detected
                      </Badge>
                    )}
                  </h4>
                  <div className="space-y-2">
                    <div className="flex flex-wrap gap-1">
                      {Array.isArray((phases.constant_detection as Record<string, unknown>)?.algorithms_detected)
                        ? ((phases.constant_detection as Record<string, unknown>).algorithms_detected as string[]).map(algo => (
                            <Badge key={algo} className="bg-blue-100 text-blue-800 border-blue-200">
                              {algo}
                            </Badge>
                          ))
                        : <span className="text-sm text-muted-foreground">None detected</span>
                      }
                    </div>
                  </div>
                </div>
              )}

              {/* Function Symbols */}
              {phases.function_symbols && (
                <div className="p-4 bg-muted/50 rounded-lg">
                  <h4 className="font-semibold mb-2 flex items-center justify-between">
                    <span>Function Symbols</span>
                    {typeof (phases.function_symbols as Record<string, unknown>)?.count === 'number' && (
                      <Badge variant="outline">
                        {Number((phases.function_symbols as Record<string, unknown>).count)} functions
                      </Badge>
                    )}
                  </h4>
                  <div className="space-y-2">
                    <div className="flex items-center gap-2">
                      <span className="text-sm text-muted-foreground">Symbols Detected:</span>
                      <Badge variant={
                        (phases.function_symbols as Record<string, unknown>)?.detected 
                          ? "default" 
                          : "secondary"
                      }>
                        {(phases.function_symbols as Record<string, unknown>)?.detected ? 'Yes' : 'No'}
                      </Badge>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-sm text-muted-foreground">Stripped Binary:</span>
                      <Badge variant={
                        (phases.function_symbols as Record<string, unknown>)?.stripped 
                          ? "destructive" 
                          : "default"
                      }>
                        {(phases.function_symbols as Record<string, unknown>)?.stripped ? 'Yes' : 'No'}
                      </Badge>
                    </div>
                  </div>
                </div>
              )}

              {/* Dynamic Analysis */}
              {phases.dynamic_analysis && (
                <div className="p-4 bg-muted/50 rounded-lg">
                  <h4 className="font-semibold mb-2">Dynamic Analysis Phase</h4>
                  {Object.keys(phases.dynamic_analysis as Record<string, unknown>).length > 0 ? (
                    <div className="space-y-2">
                      <JsonViewer 
                        data={phases.dynamic_analysis}
                        title=""
                        maxHeight="300px"
                        searchable={false}
                        downloadable={false}
                      />
                    </div>
                  ) : (
                    <p className="text-sm text-muted-foreground">
                      Dynamic analysis phase was initiated but no detailed results available.
                    </p>
                  )}
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Classification Results */}
      {classificationResults && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Brain className="w-5 h-5" />
              Classification Results
            </CardTitle>
          </CardHeader>
          <CardContent>
            <JsonViewer 
              data={classificationResults}
              title=""
              maxHeight="400px"
              searchable={true}
              downloadable={false}
            />
          </CardContent>
        </Card>
      )}

      {/* Raw Output */}
      {qilingResults.raw_output && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Activity className="w-5 h-5" />
              Execution Log
            </CardTitle>
            <CardDescription>
              Complete output from the dynamic analysis execution
            </CardDescription>
          </CardHeader>
          <CardContent>
            <pre className="bg-muted p-4 rounded-lg text-xs overflow-auto max-h-96 whitespace-pre-wrap font-mono">
              {qilingResults.raw_output as string}
            </pre>
          </CardContent>
        </Card>
      )}

      {/* Errors */}
      {/* {(qilingResults.errors || errorMessage) && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <AlertTriangle className="w-5 h-5 text-red-500" />
              Errors & Diagnostics
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {errorMessage && (
              <div>
                <h4 className="font-semibold mb-2 text-sm">Error Message:</h4>
                <div className="bg-red-50 border border-red-200 p-3 rounded-lg text-sm text-red-800">
                  {errorMessage}
                </div>
              </div>
            )}
            {qilingResults.errors && (
              <div>
                <h4 className="font-semibold mb-2 text-sm">Detailed Error Log:</h4>
                <pre className="bg-red-50 border border-red-200 p-4 rounded-lg text-xs overflow-auto max-h-96 whitespace-pre-wrap text-red-800">
                  {qilingResults.errors as string}
                </pre>
              </div>
            )}
          </CardContent>
        </Card>
      )} */}
    </div>
  );
};

// Component for Raw Data Display
const RawDataCard = ({ analysisData }: { analysisData: JobAnalysisData }) => (
  <JsonViewer 
    data={analysisData}
    title="Complete Analysis Data"
    maxHeight="800px"
    searchable={true}
    downloadable={true}
  />
);

export default JobAnalysis;