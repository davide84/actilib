% HOW TO TEST:
% imq_handle = imquest;
% imq_handle.loadCTdata('/home/cester/Data/2021-06-12_MP4_PCCT/Datasets/10mGy_FBP_80keV_R1');
% res = imquest_MercuryPhantomAutoAnalyze(imq_handle,'4.0');
% json = save_json_results('/home/cester/Data/2021-06-12_MP4_PCCT/PlotData/10mGy_FBP_80keV_R1.json', res);

function ret = save_json_results(json_file_path, res, flag_gzip)

    list_diameters = ["d160mm", "d210mm", "d260mm", "d310mm", "d360mm"];
    list_inserts = ["Air", "Water", "Bone", "Polystyrene", "Iodine"];

    % Software information
    % ---------------------------------------------------------------------
    ret.info_software = res.tool.versionInfoTable;

    % Phantom information
    % ---------------------------------------------------------------------
    pp = struct();
    pp.version = 4.0;
    pp.diameters_mm = res.PhantomDiameters;
    pp.insert_names = res.Inserts;
    pp.nyquist_frequencies = struct();
    pp.nyquist_frequencies.fx = res.ny(1);
    pp.nyquist_frequencies.fy = res.ny(2);
    ret.info_phantom = pp;

    % CT series information
    % ---------------------------------------------------------------------
    % data here is saved as an array of strings, each one resembling a
    % single key-value dictionary-like pair... which must be parsed
    
    si = struct();
    for i=1:length(res.CTSeriesSummary)
        key_value = split(res.CTSeriesSummary(i), ': ');
        si.(replace(key_value{1}, ' ', '')) = key_value{2};
    end
    si.StudyDate = datetime(si.StudyDate, 'InputFormat', 'yyyyMMdd');
    si.SeriesDate = datetime(si.SeriesDate, 'InputFormat', 'yyyyMMdd');
    si.AccessionNumber = NaN;
    si.SeriesNumber = str2num(si.SeriesNumber);
    si.AcquisitionNumber = str2num(si.AcquisitionNumber);
    si.XrayTubeCurrent = str2num(si.XrayTubeCurrent);
    si.ExposureTime = str2num(si.ExposureTime);
    si.SpiralPitchFactor = str2double(si.SpiralPitchFactor);
    si.DataCollectionDiameter = str2double(si.DataCollectionDiameter);
    si.ReconstructionDiameter = str2double(si.ReconstructionDiameter);
    tmparr = split(si.PixelSpacing(2:end-1), ', ');
    si.PixelSpacing = [str2double(tmparr(1)), str2double(tmparr(2))];
    si.ConvolutionKernel = replace(si.ConvolutionKernel, '\', '\\');
    si.SliceThickness = str2double(si.SliceThickness);
    tmparr = split(si.SeriesImageSize(2:end-1), ', ');
    si.SeriesImageSize = [str2double(tmparr(1)), str2double(tmparr(2)), str2double(tmparr(3))];
    si.SliceInterval = str2num(si.SliceInterval);
    try si.KVP = str2num(si.KVP); end
    try si.FocalSpot = str2double(si.FocalSpot); end
    ret.info_series = si;

    % Detectability Index vs Phantom Diameter
    % ---------------------------------------------------------------------
    ret.values_dprime = struct();
    for i=1:length(list_inserts)
        tmp_i = struct();
        tmp_i.dprimes = struct();
        for d=1:length(list_diameters)
            tmp_i.dprimes.(list_diameters(d)) = res.detectabilityIndex(d, i);
        end
        tmp_i.alpha = res.alphas(i);
        tmp_i.beta = res.betas(i);
        tmp_i.residual = res.residuals(i);
        tmp_i.r2 = res.R2s(i);
        ret.values_dprime.(list_inserts(i)) = tmp_i;
    end

    % Slice Position and usage flags (NPS/TTF)
    % ---------------------------------------------------------------------
    ret.values_slices = struct();
    [~, ~, z] = getCTcoordinates(res.tool.DICOMheaders);
    ret.values_slices.z = z;
    ret.values_slices.is_nps = res.NPSslice;
    ret.values_slices.is_ttf = res.TTFslice;

    % Tube Current profile
    % ---------------------------------------------------------------------
    cp = struct();
    % Create mA profile
    for i=1:res.tool.CTImageSize(3)  % loop on the axial slices
        if isfield(res.tool.DICOMheaders,'CTDIvol')
            mA(i,1) = res.tool.DICOMheaders(i).CTDIvol;
            ylab = 'CTDI_{vol} [mGy]';
            ylims = [0 2 10 50 100];
        else
            m = res.tool.DICOMheaders(i).XrayTubeCurrent;
            try
                s = res.tool.DICOMheaders(i).RevolutionTime;
            catch
                s = res.tool.DICOMheaders(i).ExposureTime/1000;
            end
            try
                p = res.tool.DICOMheaders(i).SpiralPitchFactor;
            catch
                try
                    p = res.tool.DICOMheaders(i).TableFeedPerRotation/res.tool.DICOMheaders(i).TotalCollimationWidth;
                catch
                    p=1;
                end
            end
            mA(i,1) = m*s/p;
            ylab = 'Effective mAs';
            ylims = [0 50 100 800 1000 2000];
        end
    end
    m = max(mA);
    ind = interp1(ylims,1:length(ylims),m);
    ind = floor(ind);
    if ind==length(ylims)
        ylims = [ylims(1) m*1.1];
    else
        ylims = [ylims(1) ylims(ind+1)];
    end
    cp.ma = struct();
    cp.ma.values = mA;
    cp.ma.label = ylab;
    cp.ma.limits = ylims;
    % Create WED profile
    cp.wed = getWEDfromCT(getImage(res.tool.handles.imtool),res.tool.CTpsize(1));
    % final current profile
    ret.values_current = cp;

    % Noise Properties
    % ---------------------------------------------------------------------
    ret.values_nps = struct();
    for d=1:length(res.NPSs)
        fields = ["fav", "fpeak", "noise", "NPS"];
        ret.values_nps.(list_diameters(d)) = struct();
        for f=1:length(fields)
            ret.values_nps.(list_diameters(d)).(fields(f)) = res.NPSs(d).(fields(f));
        end
        ret.values_nps.(list_diameters(d)).NPS_2D = res.NPSs(d).stats.NPS_2D;            
    end
    
    % TTF Values
    % ---------------------------------------------------------------------
    ret.values_ttf = struct();
    for i=1:size(res.TTFs, 2)  % diameters
        tmp_i = struct();
        for d=1:size(res.TTFs, 1)  % inserts
            tmp_d = struct();
            tmp_d.ESF = res.TTFs(d,i).stats.ESF.ESF;
            tmp_d.LSF = LSF_from_ESF(tmp_d.ESF);
            tmp_d.TTF = res.TTFs(d,i).TTF;
            tmp_d.contrast = res.TTFs(d,i).contrast;
            tmp_d.f10 = res.TTFs(d,i).f10;
            tmp_d.f50 = res.TTFs(d,i).f50;
            tmp_i.(list_diameters(d)) = tmp_d;
        end
        ret.values_ttf.(list_inserts(i)) = tmp_i;
    end

    % Frequency intervals for plotting
    % ---------------------------------------------------------------------
    ret.values_freq = struct();
    ret.values_freq.nps_fx = res.NPSs(1).stats.fx;
    ret.values_freq.nps_fy = res.NPSs(1).stats.fy;
    ret.values_freq.nps_f = res.NPSs(1).f;
    ret.values_freq.ttf_f = res.TTFs(1,1).f;

    % Writeout
    % ---------------------------------------------------------------------

    % conversion (separate for debugging)
    json_data = jsonencode(ret);
   
    % actual writeout
    fid=fopen(json_file_path, 'w');
    fprintf(fid, json_data);
    fclose(fid);
    
    %optional compression
    if nargin>2 & flag_gzip==true
        [save_path, json_name, ~] = fileparts(json_file_path);
        gzip_file_path = [save_path filesep json_name '.tar.gz'];
        tar(gzip_file_path, {json_file_path}, save_path);
        delete(json_file_path)
    end

end

function LSF = LSF_from_ESF(ESF)
    %Find the width of the ESF
    M=max(ESF);
    m=min(ESF);
    [~,edgePosition] = sort(abs( ESF-(M+m)/2 ));% make sure ESF is increasing
    edgeCenter = (edgePosition(1));
    if mean(ESF(1:edgeCenter))>mean(ESF(edgeCenter:end))
        E1=find(ESF>m+0.85*(M-m),1,'last');
        E2=find(ESF<m+0.15*(M-m),1,'first');
    else
        E1=find(ESF>m+0.85*(M-m),1,'first');
        E2=find(ESF<m+0.15*(M-m),1,'last');
    end
    default_hann_window_size = 15;
    w = default_hann_window_size * abs(E2-E1);
    f1=max(edgeCenter-w,1);
    f2=min(edgeCenter+w,length(ESF)-1);
    %Take derivative of ESF to get LSF
    LSF = diff(ESF);
    %Apply hann window to smooth out tails
    H = zeros(size(LSF));
    H(f1:f2) = hann(length(H(f1:f2)));
    LSF = LSF(:).*H(:);
end
