% HOW TO TEST:
% imq_handle = imquest;
% imq_handle.loadCTdata('/home/cester/Data/MercuryPhantom/Datasets/DS_5mGy_R1/80keV');
% res = imquest_MercuryPhantomAutoAnalyze(imq_handle,'4.0');
% json = save_json_results('/home/cester/Data/MercuryPhantom/PlotData/DS_5mGy_R1_80keV.json', res);

function ret = save_json_results(json_file_path, res)

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
    si.KVP = str2num(si.KVP);
    si.XrayTubeCurrent = str2num(si.XrayTubeCurrent);
    si.ExposureTime = str2num(si.ExposureTime);
    si.SpiralPitchFactor = str2double(si.SpiralPitchFactor);
    si.FocalSpot = str2double(si.FocalSpot);
    si.DataCollectionDiameter = str2double(si.DataCollectionDiameter);
    si.ReconstructionDiameter = str2double(si.ReconstructionDiameter);
    tmparr = split(si.PixelSpacing(2:end-1), ', ');
    si.PixelSpacing = [str2double(tmparr(1)), str2double(tmparr(2))];
    si.ConvolutionKernel = replace(si.ConvolutionKernel, '\', '\\');
    si.SliceThickness = str2double(si.SliceThickness);
    tmparr = split(si.SeriesImageSize(2:end-1), ', ');
    si.SeriesImageSize = [str2double(tmparr(1)), str2double(tmparr(2)), str2double(tmparr(3))];
    si.SliceInterval = str2num(si.SliceInterval);
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

    % Tube Current profile
    % ---------------------------------------------------------------------
    cp = struct();
    [~, ~, z] = getCTcoordinates(res.tool.DICOMheaders);
    cp.z = z;
    cp.nps_slices = res.NPSslice;
    cp.ttf_slices = res.TTFslice;
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

end