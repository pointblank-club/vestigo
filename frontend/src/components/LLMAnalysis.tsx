import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Brain, CheckCircle2, AlertTriangle, XCircle, Lightbulb, FileSearch, Zap, FileText, Activity, Download } from "lucide-react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Button } from "@/components/ui/button";
import { useState, useEffect } from "react";

interface LLMAnalysisProps {
  llmData: Record<string, unknown> | null;
  qilingData?: Record<string, unknown> | null;
  jobId?: string;
}

interface StraceLogData {
  job_id: string;
  binary_name: string;
  strace_log_path: string;
  strace_log_name: string;
  file_size: number;
  content: string;
  lines: number;
  available_logs: string[];
}

interface AnalysisLogData {
  job_id: string;
  binary_name: string;
  analysis_log_path: string;
  analysis_log_name: string;
  file_size: number;
  content: string;
  lines: number;
  available_logs: string[];
}

import { API_CONFIG } from "@/config/api";

export const LLMAnalysisCard = ({ llmData, qilingData, jobId }: LLMAnalysisProps) => {
  const [straceLog, setStraceLog] = useState<StraceLogData | null>(null);
  const [analysisLog, setAnalysisLog] = useState<AnalysisLogData | null>(null);
  const [loadingStrace, setLoadingStrace] = useState(false);
  const [loadingAnalysis, setLoadingAnalysis] = useState(false);
  const [straceError, setStraceError] = useState<string | null>(null);
  const [analysisError, setAnalysisError] = useState<string | null>(null);

  // Fetch strace logs when component mounts
  useEffect(() => {
    const fetchStraceLogs = async () => {
      if (!jobId) return;
      
      setLoadingStrace(true);
      setStraceError(null);
      
      try {
        const response = await fetch(`${API_CONFIG.BASE_URL}/job/${jobId}/strace-logs`);
        if (!response.ok) {
          if (response.status === 404) {
            setStraceError("No strace logs found for this binary");
          } else {
            setStraceError("Failed to fetch strace logs");
          }
          return;
        }
        
        const data = await response.json();
        setStraceLog(data);
      } catch (error) {
        console.error("Error fetching strace logs:", error);
        setStraceError("Error loading strace logs");
      } finally {
        setLoadingStrace(false);
      }
    };

    fetchStraceLogs();
  }, [jobId]);

  // Fetch analysis logs when component mounts
  useEffect(() => {
    const fetchAnalysisLogs = async () => {
      if (!jobId) return;
      
      setLoadingAnalysis(true);
      setAnalysisError(null);
      
      try {
        const response = await fetch(`${API_CONFIG.BASE_URL}/job/${jobId}/analysis-logs`);
        if (!response.ok) {
          if (response.status === 404) {
            setAnalysisError("No analysis logs found for this binary");
          } else {
            setAnalysisError("Failed to fetch analysis logs");
          }
          return;
        }
        
        const data = await response.json();
        setAnalysisLog(data);
      } catch (error) {
        console.error("Error fetching analysis logs:", error);
        setAnalysisError("Error loading analysis logs");
      } finally {
        setLoadingAnalysis(false);
      }
    };

    fetchAnalysisLogs();
  }, [jobId]);

  // Download strace log
  const downloadStraceLog = () => {
    if (!straceLog) return;
    
    const blob = new Blob([straceLog.content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = straceLog.strace_log_name;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  // Download analysis log
  const downloadAnalysisLog = () => {
    if (!analysisLog) return;
    
    const blob = new Blob([analysisLog.content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = analysisLog.analysis_log_name;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  // Fallback component when Agent is not available
  const FallbackAnalysisView = () => {
    const qilingResults = qilingData?.qiling_dynamic_results as Record<string, unknown> | null;
    const rawOutput = qilingResults?.raw_output as string;
    const errors = qilingResults?.errors as string;
    const phases = qilingResults?.phases as Record<string, unknown> | null;
    const verdict = qilingResults?.verdict as Record<string, unknown> | null;

    return (
      <div className="space-y-6">
        <Card className="bg-card border-border">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Brain className="w-5 h-5 text-muted-foreground" />
              Agent Analysis Not Available
            </CardTitle>
            <CardDescription>
              Showing raw analysis data instead
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Alert>
              <AlertTriangle className="h-4 w-4" />
              <AlertTitle>Agent Analysis Unavailable</AlertTitle>
              <AlertDescription>
                {!llmData 
                  ? "Agent analysis has not been performed on this binary yet." 
                  : "Agent classification data could not be parsed. Showing fallback data below."}
              </AlertDescription>
            </Alert>
          </CardContent>
        </Card>

        {/* Qiling Analysis Results */}
        {qilingResults && (
          <Card className="bg-card border-border">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Activity className="w-5 h-5 text-blue-500" />
                Qiling Dynamic Analysis Results
              </CardTitle>
              <CardDescription>
                Raw crypto detection results from Qiling framework
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Verdict */}
              {verdict && (
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 p-4 bg-secondary/30 rounded-lg">
                  <div>
                    <p className="text-sm text-muted-foreground mb-1">Crypto Detected</p>
                    <Badge variant={verdict.crypto_detected ? "default" : "outline"}>
                      {verdict.crypto_detected ? 'Yes' : 'No'}
                    </Badge>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground mb-1">Confidence</p>
                    <Badge variant="outline">{verdict.confidence as string || 'Unknown'}</Badge>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground mb-1">Confidence Score</p>
                    <span className="text-lg font-bold">{verdict.confidence_score as number || 0}%</span>
                  </div>
                </div>
              )}

              {/* Detection Phases */}
              {phases && (
                <div className="space-y-3">
                  <h3 className="text-lg font-semibold">Detection Phases</h3>
                  
                  <Tabs defaultValue="yara" className="w-full">
                    <TabsList className="grid w-full grid-cols-4">
                      <TabsTrigger value="yara">YARA</TabsTrigger>
                      <TabsTrigger value="constants">Constants</TabsTrigger>
                      <TabsTrigger value="functions">Functions</TabsTrigger>
                      <TabsTrigger value="packer">Packer</TabsTrigger>
                    </TabsList>

                    <TabsContent value="yara" className="space-y-3">
                      {phases.yara_analysis && (
                        <Card className="bg-secondary/30">
                          <CardContent className="pt-4">
                            <div className="space-y-2">
                              <div>
                                <span className="text-sm text-muted-foreground">Detected:</span>
                                <div className="flex flex-wrap gap-1 mt-1">
                                  {(phases.yara_analysis as Record<string, unknown>).detected && 
                                   Array.isArray((phases.yara_analysis as Record<string, unknown>).detected) &&
                                   ((phases.yara_analysis as Record<string, unknown>).detected as string[]).map((item, idx) => (
                                    <Badge key={idx} variant="outline">{item}</Badge>
                                  ))}
                                </div>
                              </div>
                              <p className="text-sm">
                                <span className="text-muted-foreground">Total Matches:</span>{' '}
                                {(phases.yara_analysis as Record<string, unknown>).total_matches as number || 0}
                              </p>
                              <p className="text-sm">
                                <span className="text-muted-foreground">Scan Time:</span>{' '}
                                {(phases.yara_analysis as Record<string, unknown>).scan_time as number || 0}s
                              </p>
                            </div>
                          </CardContent>
                        </Card>
                      )}
                    </TabsContent>

                    <TabsContent value="constants" className="space-y-3">
                      {phases.constant_detection && (
                        <Card className="bg-secondary/30">
                          <CardContent className="pt-4">
                            <div className="space-y-2">
                              <p className="text-sm">
                                <span className="text-muted-foreground">Algorithms Detected:</span>
                              </p>
                              <div className="flex flex-wrap gap-1">
                                {(phases.constant_detection as Record<string, unknown>).algorithms_detected && 
                                 Array.isArray((phases.constant_detection as Record<string, unknown>).algorithms_detected) &&
                                 ((phases.constant_detection as Record<string, unknown>).algorithms_detected as string[]).map((algo, idx) => (
                                  <Badge key={idx} className="bg-blue-500/10 text-blue-500">{algo}</Badge>
                                ))}
                              </div>
                              <p className="text-sm mt-2">
                                <span className="text-muted-foreground">Count:</span>{' '}
                                {(phases.constant_detection as Record<string, unknown>).count as number || 0}
                              </p>
                            </div>
                          </CardContent>
                        </Card>
                      )}
                    </TabsContent>

                    <TabsContent value="functions" className="space-y-3">
                      {phases.function_symbols && (
                        <Card className="bg-secondary/30">
                          <CardContent className="pt-4">
                            <div className="space-y-2">
                              <p className="text-sm">
                                <span className="text-muted-foreground">Detected:</span>{' '}
                                {(phases.function_symbols as Record<string, unknown>).detected ? 'Yes' : 'No'}
                              </p>
                              <p className="text-sm">
                                <span className="text-muted-foreground">Count:</span>{' '}
                                {(phases.function_symbols as Record<string, unknown>).count as number || 0}
                              </p>
                            </div>
                          </CardContent>
                        </Card>
                      )}
                    </TabsContent>

                    <TabsContent value="packer" className="space-y-3">
                      {phases.packer_detection && (
                        <Card className="bg-secondary/30">
                          <CardContent className="pt-4">
                            <div className="space-y-2">
                              <p className="text-sm">
                                <span className="text-muted-foreground">Packed:</span>{' '}
                                {(phases.packer_detection as Record<string, unknown>).packed ? 'Yes' : 'No'}
                              </p>
                              {(phases.packer_detection as Record<string, unknown>).packer && (
                                <p className="text-sm">
                                  <span className="text-muted-foreground">Packer:</span>{' '}
                                  {(phases.packer_detection as Record<string, unknown>).packer as string}
                                </p>
                              )}
                            </div>
                          </CardContent>
                        </Card>
                      )}
                    </TabsContent>
                  </Tabs>
                </div>
              )}

              {/* Reasons */}
              {verdict && verdict.reasons && Array.isArray(verdict.reasons) && (
                <div>
                  <h3 className="text-lg font-semibold mb-2">Detection Reasons</h3>
                  <ul className="list-disc list-inside space-y-1">
                    {(verdict.reasons as string[]).map((reason, idx) => (
                      <li key={idx} className="text-sm text-muted-foreground">{reason}</li>
                    ))}
                  </ul>
                </div>
              )}
            </CardContent>
          </Card>
        )}

        {/* Raw Output / Strace Logs */}
        {rawOutput && (
          <Card className="bg-card border-border">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <FileText className="w-5 h-5 text-green-500" />
                Raw Analysis Output
              </CardTitle>
              <CardDescription>
                Console output from Qiling dynamic analysis including strace logs
              </CardDescription>
            </CardHeader>
            <CardContent>
              <ScrollArea className="h-96 w-full rounded-md border">
                <pre className="p-4 text-xs font-mono whitespace-pre-wrap">
                  {rawOutput}
                </pre>
              </ScrollArea>
            </CardContent>
          </Card>
        )}

        {/* Errors */}
        {/* {errors && (
          <Card className="bg-card border-destructive/20">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-destructive">
                <XCircle className="w-5 h-5" />
                Analysis Errors
              </CardTitle>
              <CardDescription>
                Errors encountered during Qiling analysis
              </CardDescription>
            </CardHeader>
            <CardContent>
              <ScrollArea className="h-64 w-full rounded-md border border-destructive/20">
                <pre className="p-4 text-xs font-mono whitespace-pre-wrap text-destructive">
                  {errors}
                </pre>
              </ScrollArea>
            </CardContent>
          </Card>
        )} */}

        {/* Analysis Logs from API */}
        {analysisLog && (
          <Card className="bg-card border-border">
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="flex items-center gap-2">
                    <Activity className="w-5 h-5 text-purple-500" />
                    Raw Analysis Output
                  </CardTitle>
                  <CardDescription>
                    Complete analysis output including YARA, constants, and memory dumps for {analysisLog.binary_name}
                  </CardDescription>
                </div>
                <Button 
                  variant="outline" 
                  size="sm" 
                  onClick={downloadAnalysisLog}
                  className="gap-2"
                >
                  <Download className="w-4 h-4" />
                  Download
                </Button>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 p-4 bg-secondary/30 rounded-lg">
                <div>
                  <p className="text-xs text-muted-foreground mb-1">Log File</p>
                  <p className="text-sm font-mono truncate">{analysisLog.analysis_log_name}</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground mb-1">File Size</p>
                  <p className="text-sm">{(analysisLog.file_size / 1024).toFixed(2)} KB</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground mb-1">Total Lines</p>
                  <p className="text-sm font-bold">{analysisLog.lines.toLocaleString()}</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground mb-1">Available Logs</p>
                  <p className="text-sm">{analysisLog.available_logs.length}</p>
                </div>
              </div>

              <Alert className="bg-purple-500/10 border-purple-500/20">
                <FileSearch className="h-4 w-4 text-purple-500" />
                <AlertTitle className="text-purple-500">Multi-Phase Analysis</AlertTitle>
                <AlertDescription className="text-purple-500/80">
                  This log contains YARA rule matches, cryptographic constant detection, function analysis, and memory dump analysis.
                </AlertDescription>
              </Alert>

              <Tabs defaultValue="preview" className="w-full">
                <TabsList className="grid w-full grid-cols-2">
                  <TabsTrigger value="preview">Preview (First 200 lines)</TabsTrigger>
                  <TabsTrigger value="full">Full Log</TabsTrigger>
                </TabsList>

                <TabsContent value="preview">
                  <ScrollArea className="h-96 w-full rounded-md border">
                    <pre className="p-4 text-xs font-mono whitespace-pre-wrap">
                      {analysisLog.content.split('\n').slice(0, 200).join('\n')}
                      {analysisLog.lines > 200 && '\n\n... (showing first 200 lines, switch to Full Log tab or download for complete content)'}
                    </pre>
                  </ScrollArea>
                </TabsContent>

                <TabsContent value="full">
                  <ScrollArea className="h-96 w-full rounded-md border">
                    <pre className="p-4 text-xs font-mono whitespace-pre-wrap">
                      {analysisLog.content}
                    </pre>
                  </ScrollArea>
                </TabsContent>
              </Tabs>

              <p className="text-xs text-muted-foreground">
                <span className="font-semibold">Path:</span> {analysisLog.analysis_log_path}
              </p>
            </CardContent>
          </Card>
        )}

        {/* Loading Analysis */}
        {loadingAnalysis && (
          <Card className="bg-card border-border">
            <CardContent className="pt-6">
              <Alert>
                <Activity className="h-4 w-4 animate-pulse" />
                <AlertTitle>Loading Analysis Logs</AlertTitle>
                <AlertDescription>
                  Fetching raw analysis output...
                </AlertDescription>
              </Alert>
            </CardContent>
          </Card>
        )}

        {/* Analysis Error */}
        {analysisError && !loadingAnalysis && (
          <Card className="bg-card border-border">
            <CardContent className="pt-6">
              <Alert>
                <AlertTriangle className="h-4 w-4" />
                <AlertTitle>Analysis Logs Not Available</AlertTitle>
                <AlertDescription>
                  {analysisError}
                </AlertDescription>
              </Alert>
            </CardContent>
          </Card>
        )}

        {/* Strace Logs from API */}
        {straceLog && (
          <Card className="bg-card border-border">
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="flex items-center gap-2">
                    <FileText className="w-5 h-5 text-blue-500" />
                    Strace System Call Logs
                  </CardTitle>
                  <CardDescription>
                    Native syscall trace for {straceLog.binary_name}
                  </CardDescription>
                </div>
                <Button 
                  variant="outline" 
                  size="sm" 
                  onClick={downloadStraceLog}
                  className="gap-2"
                >
                  <Download className="w-4 h-4" />
                  Download
                </Button>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 p-4 bg-secondary/30 rounded-lg">
                <div>
                  <p className="text-xs text-muted-foreground mb-1">Log File</p>
                  <p className="text-sm font-mono truncate">{straceLog.strace_log_name}</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground mb-1">File Size</p>
                  <p className="text-sm">{(straceLog.file_size / 1024).toFixed(2)} KB</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground mb-1">Total Lines</p>
                  <p className="text-sm font-bold">{straceLog.lines.toLocaleString()}</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground mb-1">Available Logs</p>
                  <p className="text-sm">{straceLog.available_logs.length}</p>
                </div>
              </div>

              <ScrollArea className="h-96 w-full rounded-md border">
                <pre className="p-4 text-xs font-mono whitespace-pre-wrap">
                  {straceLog.content}
                </pre>
              </ScrollArea>

              <p className="text-xs text-muted-foreground">
                <span className="font-semibold">Path:</span> {straceLog.strace_log_path}
              </p>
            </CardContent>
          </Card>
        )}

        {/* Loading Strace */}
        {loadingStrace && (
          <Card className="bg-card border-border">
            <CardContent className="pt-6">
              <Alert>
                <Activity className="h-4 w-4 animate-pulse" />
                <AlertTitle>Loading Strace Logs</AlertTitle>
                <AlertDescription>
                  Fetching system call traces from analysis...
                </AlertDescription>
              </Alert>
            </CardContent>
          </Card>
        )}

        {/* Strace Error */}
        {straceError && !loadingStrace && (
          <Card className="bg-card border-border">
            <CardContent className="pt-6">
              <Alert>
                <AlertTriangle className="h-4 w-4" />
                <AlertTitle>Strace Logs Not Available</AlertTitle>
                <AlertDescription>
                  {straceError}
                </AlertDescription>
              </Alert>
            </CardContent>
          </Card>
        )}

        {/* No Data Available */}
        {!qilingResults && (
          <Card className="bg-card border-border">
            <CardContent className="pt-6">
              <Alert>
                <AlertTriangle className="h-4 w-4" />
                <AlertTitle>No Analysis Data Available</AlertTitle>
                <AlertDescription>
                  Neither Agent analysis nor Qiling dynamic analysis results are available for this binary.
                </AlertDescription>
              </Alert>
            </CardContent>
          </Card>
        )}
      </div>
    );
  };

  // If no Agent data at all, show fallback
  if (!llmData) {
    return <FallbackAnalysisView />;
  }

  const status = llmData.status as string;
  const llmClassification = llmData.llm_classification as Record<string, unknown> | null;
  const qilingContext = llmData.qiling_context as Record<string, unknown> | null;
  const model = llmData.model as string || 'gpt-4o';
  const straceLogPath = llmData.strace_log_path as string;

  // Handle disabled or failed status - show fallback
  if (status === 'disabled') {
    return <FallbackAnalysisView />;
  }

  if (status === 'failed') {
    return <FallbackAnalysisView />;
  }

  // If classification parsing failed or is invalid, show fallback
  if (!llmClassification) {
    return <FallbackAnalysisView />;
  }

  const cryptoClassification = llmClassification.crypto_classification as string;
  const cryptoAlgorithm = llmClassification.crypto_algorithm as string;
  const isProprietary = llmClassification.is_proprietary as boolean;
  const reasoning = llmClassification.reasoning as string;
  const confidence = llmClassification.confidence as number;
  const proprietaryAnalysis = llmClassification.proprietary_analysis as Record<string, unknown> | null;

  // Determine classification color and icon
  const getClassificationBadge = (classification: string) => {
    switch (classification) {
      case 'STANDARD_CRYPTO':
        return (
          <Badge className="bg-blue-500/10 text-blue-500 border-blue-500/20">
            <CheckCircle2 className="w-3 h-3 mr-1" />
            Standard Crypto
          </Badge>
        );
      case 'PROPRIETARY_CRYPTO':
        return (
          <Badge className="bg-orange-500/10 text-orange-500 border-orange-500/20">
            <Zap className="w-3 h-3 mr-1" />
            Proprietary Crypto
          </Badge>
        );
      case 'NON_CRYPTO':
        return (
          <Badge className="bg-green-500/10 text-green-500 border-green-500/20">
            <CheckCircle2 className="w-3 h-3 mr-1" />
            No Crypto Detected
          </Badge>
        );
      default:
        return (
          <Badge variant="outline">
            {classification || 'Unknown'}
          </Badge>
        );
    }
  };

  const getConfidenceColor = (conf: number) => {
    if (conf >= 0.8) return 'text-green-500';
    if (conf >= 0.6) return 'text-yellow-500';
    return 'text-orange-500';
  };

  return (
    <div className="space-y-6">
      {/* LLM Analysis Metadata */}
      {llmData.timestamp && (
        <Card className="bg-card border-border">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Brain className="w-5 h-5 text-muted-foreground" />
              Analysis Metadata
            </CardTitle>
            <CardDescription>
              Two-stage analysis combining raw analysis output with AI-powered strace classification
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 p-4 bg-secondary/30 rounded-lg">
              <div>
                <p className="text-xs text-muted-foreground mb-1">Analysis Timestamp</p>
                <p className="text-sm font-mono">
                  {llmData.timestamp ? new Date(llmData.timestamp as string).toLocaleString() : 'N/A'}
                </p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground mb-1">Analysis File</p>
                <p className="text-sm font-mono truncate" title={llmData.analysis_file as string}>
                  {llmData.analysis_file ? (llmData.analysis_file as string).split('/').pop() : 'N/A'}
                </p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground mb-1">Strace File</p>
                <p className="text-sm font-mono truncate" title={llmData.strace_file as string}>
                  {llmData.strace_file ? (llmData.strace_file as string).split('/').pop() : 'N/A'}
                </p>
              </div>
            </div>
            <Alert className="bg-blue-500/10 border-blue-500/20">
              <FileSearch className="h-4 w-4 text-blue-500" />
              <AlertTitle className="text-blue-500">Two-Stage Analysis</AlertTitle>
              <AlertDescription className="text-blue-500/80">
                This analysis combines raw static analysis output (YARA, constants, memory dumps) with AI-powered runtime trace classification.
              </AlertDescription>
            </Alert>
          </CardContent>
        </Card>
      )}

      {/* Main Classification Card */}
      <Card className="bg-card border-border">
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <Brain className="w-5 h-5 text-primary" />
                Agent Crypto Analysis
              </CardTitle>
              {/* <CardDescription>
                AI-powered classification using {model}
              </CardDescription> */}
            </div>
            {getClassificationBadge(cryptoClassification)}
          </div>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Algorithm Detection */}
          <div>
            <h3 className="text-lg font-semibold mb-2">Detected Algorithm</h3>
            <div className="flex items-center gap-2">
              <Badge variant="outline" className="text-lg px-4 py-2">
                {cryptoAlgorithm || 'None'}
              </Badge>
              {isProprietary && (
                <Badge className="bg-orange-500/10 text-orange-500 border-orange-500/20">
                  Custom Implementation
                </Badge>
              )}
            </div>
          </div>

          {/* Confidence Score */}
          <div>
            <h3 className="text-lg font-semibold mb-2">Confidence Score</h3>
            <div className="flex items-center gap-4">
              <div className="flex-1">
                <div className="w-full bg-secondary h-3 rounded-full overflow-hidden">
                  <div
                    className={`h-3 ${
                      confidence >= 0.8
                        ? 'bg-green-500'
                        : confidence >= 0.6
                        ? 'bg-yellow-500'
                        : 'bg-orange-500'
                    }`}
                    style={{ width: `${confidence * 100}%` }}
                  />
                </div>
              </div>
              <span className={`text-2xl font-bold ${getConfidenceColor(confidence)}`}>
                {(confidence * 100).toFixed(1)}%
              </span>
            </div>
          </div>

          {/* Agent Reasoning */}
          <div>
            <h3 className="text-lg font-semibold mb-2 flex items-center gap-2">
              <Lightbulb className="w-4 h-4" />
              Analysis Reasoning
            </h3>
            <p className="text-muted-foreground leading-relaxed">
              {reasoning}
            </p>
          </div>

          {/* Strace Source */}
          {straceLogPath && (
            <div>
              <h3 className="text-sm font-semibold mb-1 flex items-center gap-2 text-muted-foreground">
                <FileSearch className="w-3 h-3" />
                Strace Log Source
              </h3>
              <p className="text-xs font-mono text-muted-foreground break-all">
                {straceLogPath}
              </p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Proprietary Analysis Details */}
      {isProprietary && proprietaryAnalysis && (
        <Card className="bg-card border-orange-500/20">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-orange-500">
              <Zap className="w-5 h-5" />
              Proprietary Crypto Analysis
            </CardTitle>
            <CardDescription>
              Detailed analysis of custom cryptographic implementation
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Summary */}
            {proprietaryAnalysis.summary && (
              <div>
                <h3 className="text-lg font-semibold mb-2">Summary</h3>
                <p className="text-muted-foreground">
                  {proprietaryAnalysis.summary as string}
                </p>
              </div>
            )}

            {/* Evidence */}
            {proprietaryAnalysis.evidence && Array.isArray(proprietaryAnalysis.evidence) && proprietaryAnalysis.evidence.length > 0 && (
              <div>
                <h3 className="text-lg font-semibold mb-3">Supporting Evidence</h3>
                <div className="space-y-3">
                  {(proprietaryAnalysis.evidence as Array<Record<string, unknown>>).map((evidence, idx) => (
                    <Card key={idx} className="bg-secondary/30 border-border">
                      <CardContent className="pt-4">
                        <p className="font-semibold mb-2">{evidence.fact as string}</p>
                        <p className="text-sm text-muted-foreground">
                          {evidence.support as string}
                        </p>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Qiling Context Comparison */}
      {qilingContext && (
        <Card className="bg-card border-border">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FileSearch className="w-5 h-5" />
              Static Analysis Correlation
            </CardTitle>
            <CardDescription>
              Cross-reference with Qiling static analysis results
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <p className="text-sm text-muted-foreground mb-1">
                  Qiling Crypto Detected
                </p>
                <Badge variant={qilingContext.crypto_detected ? "default" : "outline"}>
                  {qilingContext.crypto_detected ? 'Yes' : 'No'}
                </Badge>
              </div>
              <div>
                <p className="text-sm text-muted-foreground mb-1">
                  Static Algorithms Detected
                </p>
                <div className="flex flex-wrap gap-1">
                  {qilingContext.detected_algorithms && Array.isArray(qilingContext.detected_algorithms) && qilingContext.detected_algorithms.length > 0 ? (
                    (qilingContext.detected_algorithms as string[]).map((algo, idx) => (
                      <Badge key={idx} variant="outline" className="text-xs">
                        {algo}
                      </Badge>
                    ))
                  ) : (
                    <span className="text-sm text-muted-foreground">None</span>
                  )}
                </div>
              </div>
            </div>

            {/* Agreement Analysis */}
            {qilingContext.crypto_detected && cryptoClassification !== 'NON_CRYPTO' && (
              <Alert className="bg-green-500/10 border-green-500/20">
                <CheckCircle2 className="h-4 w-4 text-green-500" />
                <AlertTitle className="text-green-500">Analysis Agreement</AlertTitle>
                <AlertDescription className="text-green-500/80">
                  Agent analysis confirms crypto detection from static analysis
                </AlertDescription>
              </Alert>
            )}

            {qilingContext.crypto_detected && cryptoClassification === 'NON_CRYPTO' && (
              <Alert className="bg-yellow-500/10 border-yellow-500/20">
                <AlertTriangle className="h-4 w-4 text-yellow-500" />
                <AlertTitle className="text-yellow-500">Analysis Divergence</AlertTitle>
                <AlertDescription className="text-yellow-500/80">
                  Static analysis detected crypto, but Agent found no crypto behavior in runtime traces
                </AlertDescription>
              </Alert>
            )}
          </CardContent>
        </Card>
      )}

      {/* Analysis Logs */}
      {analysisLog && (
        <Card className="bg-card border-border">
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="flex items-center gap-2">
                  <Activity className="w-5 h-5 text-purple-500" />
                  Raw Analysis Output
                </CardTitle>
                <CardDescription>
                  Complete multi-phase analysis including YARA, constants, and memory analysis
                </CardDescription>
              </div>
              <Button 
                variant="outline" 
                size="sm" 
                onClick={downloadAnalysisLog}
                className="gap-2"
              >
                <Download className="w-4 h-4" />
                Download
              </Button>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <Alert className="bg-purple-500/10 border-purple-500/20">
              <FileSearch className="h-4 w-4 text-purple-500" />
              <AlertTitle className="text-purple-500">Static Analysis Baseline</AlertTitle>
              <AlertDescription className="text-purple-500/80">
                This raw analysis output was combined with strace logs to generate the Agent classification.
              </AlertDescription>
            </Alert>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 p-4 bg-secondary/30 rounded-lg">
              <div>
                <p className="text-xs text-muted-foreground mb-1">Log File</p>
                <p className="text-sm font-mono truncate">{analysisLog.analysis_log_name}</p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground mb-1">File Size</p>
                <p className="text-sm">{(analysisLog.file_size / 1024).toFixed(2)} KB</p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground mb-1">Total Lines</p>
                <p className="text-sm font-bold">{analysisLog.lines.toLocaleString()}</p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground mb-1">Available Logs</p>
                <p className="text-sm">{analysisLog.available_logs.length}</p>
              </div>
            </div>

            <Tabs defaultValue="preview" className="w-full">
              <TabsList className="grid w-full grid-cols-2">
                <TabsTrigger value="preview">Preview (First 200 lines)</TabsTrigger>
                <TabsTrigger value="full">Full Log</TabsTrigger>
              </TabsList>

              <TabsContent value="preview">
                <ScrollArea className="h-96 w-full rounded-md border">
                  <pre className="p-4 text-xs font-mono whitespace-pre-wrap">
                    {analysisLog.content.split('\n').slice(0, 200).join('\n')}
                    {analysisLog.lines > 200 && '\n\n... (showing first 200 lines, switch to Full Log tab or download for complete content)'}
                  </pre>
                </ScrollArea>
              </TabsContent>

              <TabsContent value="full">
                <ScrollArea className="h-96 w-full rounded-md border">
                  <pre className="p-4 text-xs font-mono whitespace-pre-wrap">
                    {analysisLog.content}
                  </pre>
                </ScrollArea>
              </TabsContent>
            </Tabs>

            <p className="text-xs text-muted-foreground">
              <span className="font-semibold">Source:</span> {analysisLog.analysis_log_path}
            </p>
          </CardContent>
        </Card>
      )}

      {/* Strace Logs */}
      {straceLog && (
        <Card className="bg-card border-border">
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="flex items-center gap-2">
                  <FileText className="w-5 h-5 text-blue-500" />
                  Strace System Call Logs
                </CardTitle>
                <CardDescription>
                  Raw syscall traces used for Agent analysis
                </CardDescription>
              </div>
              <Button 
                variant="outline" 
                size="sm" 
                onClick={downloadStraceLog}
                className="gap-2"
              >
                <Download className="w-4 h-4" />
                Download
              </Button>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <Alert className="bg-blue-500/10 border-blue-500/20">
              <FileSearch className="h-4 w-4 text-blue-500" />
              <AlertTitle className="text-blue-500">Analysis Source Data</AlertTitle>
              <AlertDescription className="text-blue-500/80">
                These syscall traces were analyzed by the Agent to produce the classification above.
              </AlertDescription>
            </Alert>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 p-4 bg-secondary/30 rounded-lg">
              <div>
                <p className="text-xs text-muted-foreground mb-1">Log File</p>
                <p className="text-sm font-mono truncate">{straceLog.strace_log_name}</p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground mb-1">File Size</p>
                <p className="text-sm">{(straceLog.file_size / 1024).toFixed(2)} KB</p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground mb-1">Total Lines</p>
                <p className="text-sm font-bold">{straceLog.lines.toLocaleString()}</p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground mb-1">Available Logs</p>
                <p className="text-sm">{straceLog.available_logs.length}</p>
              </div>
            </div>

            <Tabs defaultValue="preview" className="w-full">
              <TabsList className="grid w-full grid-cols-2">
                <TabsTrigger value="preview">Preview (First 100 lines)</TabsTrigger>
                <TabsTrigger value="full">Full Log</TabsTrigger>
              </TabsList>

              <TabsContent value="preview">
                <ScrollArea className="h-96 w-full rounded-md border">
                  <pre className="p-4 text-xs font-mono whitespace-pre-wrap">
                    {straceLog.content.split('\n').slice(0, 100).join('\n')}
                    {straceLog.lines > 100 && '\n\n... (showing first 100 lines, switch to Full Log tab or download for complete content)'}
                  </pre>
                </ScrollArea>
              </TabsContent>

              <TabsContent value="full">
                <ScrollArea className="h-96 w-full rounded-md border">
                  <pre className="p-4 text-xs font-mono whitespace-pre-wrap">
                    {straceLog.content}
                  </pre>
                </ScrollArea>
              </TabsContent>
            </Tabs>

            <p className="text-xs text-muted-foreground">
              <span className="font-semibold">Source:</span> {straceLog.strace_log_path}
            </p>
          </CardContent>
        </Card>
      )}

      {/* Loading Strace */}
      {loadingStrace && (
        <Card className="bg-card border-border">
          <CardContent className="pt-6">
            <Alert>
              <Activity className="h-4 w-4 animate-pulse" />
              <AlertTitle>Loading Strace Logs</AlertTitle>
              <AlertDescription>
                Fetching system call traces...
              </AlertDescription>
            </Alert>
          </CardContent>
        </Card>
      )}
    </div>
  );
};
